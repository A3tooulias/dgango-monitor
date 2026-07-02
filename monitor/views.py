from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Device, Reading, ThresholdRule
from .serializers import DeviceSerializer, ReadingInSerializer, ReadingOutSerializer, ThresholdRuleSerializer
from .services import evaluate_reading, maybe_notify


class IngestReadingView(APIView):
    """
    POST /api/ingest/
    Header:  X-API-Key: <device api key>
    Body:    {"temperature": 32.4, "humidity": 61.2}

    This is the endpoint your WiFi sensors (ESP32, Lascar EL-WiFi-style
    loggers, etc.) call every time they take a reading. It stores the
    reading, evaluates it against your threshold array, and fires a
    Viber/SMS alert if needed.
    """

    def post(self, request):
        api_key = request.headers.get("X-API-Key") or request.data.get("api_key")
        if not api_key:
            return Response({"detail": "Missing X-API-Key header."}, status=401)

        device = Device.objects.filter(api_key=api_key, is_active=True).first()
        if device is None:
            return Response({"detail": "Invalid or inactive API key."}, status=403)

        serializer = ReadingInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        temperature = serializer.validated_data["temperature"]
        humidity = serializer.validated_data["humidity"]
        created_at = serializer.validated_data.get("timestamp", timezone.now())

        rule = evaluate_reading(temperature, humidity)
        signal_level = rule.name if rule else "Ασφαλές"
        severity = rule.severity if rule else 0

        reading = Reading.objects.create(
            device=device,
            temperature=temperature,
            humidity=humidity,
            signal_level=signal_level,
            severity=severity,
            matched_rule=rule,
            created_at=created_at,
        )

        maybe_notify(device, rule, reading)

        device.last_seen = created_at
        device.last_temperature = temperature
        device.last_humidity = humidity
        device.last_signal_level = signal_level
        device.last_severity = severity
        device.save(update_fields=[
            "last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity",
        ])

        return Response(
            {
                "stored": True,
                "signal_level": signal_level,
                "severity": severity,
                "message": rule.message if rule else "Conditions normal.",
                "work_break_schedule": rule.work_break_schedule if rule else "",
            },
            status=201,
        )


class DeviceListView(APIView):
    """GET /api/devices/  -> all devices + their latest cached status."""

    def get(self, request):
        devices = Device.objects.filter(is_active=True).order_by("name")
        return Response(DeviceSerializer(devices, many=True).data)


class DeviceReadingsView(APIView):
    """
    GET /api/devices/<id>/readings/?minutes=120
    Returns readings for the last N minutes (default 120) for charting.
    Poll this every 5-10 minutes from the dashboard (or any client) to
    redraw the temperature/humidity chart.
    """

    def get(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        minutes = int(request.query_params.get("minutes", 120))
        since = timezone.now() - timezone.timedelta(minutes=minutes)
        readings = device.readings.filter(created_at__gte=since).order_by("created_at")
        return Response(
            {
                "device": DeviceSerializer(device).data,
                "readings": ReadingOutSerializer(readings, many=True).data,
            }
        )


def dashboard(request):
    """Main page: device picker + live chart + current signal banner."""
    devices = Device.objects.filter(is_active=True).order_by("name")
    return render(request, "monitor/dashboard.html", {"devices": devices})


def thresholds_page(request):
    """Settings page where you define your own risk levels (no admin needed)."""
    return render(request, "monitor/thresholds.html")


class ThresholdRuleListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/thresholds/  -> all your risk levels, most dangerous first
    POST /api/thresholds/  -> add a new level
    """
    queryset = ThresholdRule.objects.order_by("-severity")
    serializer_class = ThresholdRuleSerializer


class ThresholdRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/thresholds/<id>/  -> edit or remove one level
    """
    queryset = ThresholdRule.objects.all()
    serializer_class = ThresholdRuleSerializer
