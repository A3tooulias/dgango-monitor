import datetime
import logging

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .heat_table_preset import MODERATE_WORK_TABLE
from .models import Device, HeatIndexRow, RiskLevel
from .serializers import (
    DeviceSerializer, HeatIndexRowSerializer, ReadingInSerializer,
    ReadingOutSerializer, RiskLevelSerializer,
)
from .services import record_reading

logger = logging.getLogger(__name__)


class IngestReadingView(APIView):
    """
    POST /api/ingest/
    Header:  X-API-Key: <το api_key της συσκευής, από το admin>
    Σώμα:    {"temperature": 32.4, "humidity": 61.2}

    Εδώ στέλνει δεδομένα ο κάθε αισθητήρας κάθε φορά που παίρνει μέτρηση
    (δικό μας JSON API - π.χ. για DIY ESP32, ή για δοκιμές με curl/simulate_device).
    """

    def post(self, request):
        api_key = request.headers.get("X-API-Key") or request.data.get("api_key")
        if not api_key:
            return Response({"detail": "Λείπει το header X-API-Key."}, status=401)

        device = Device.objects.filter(api_key=api_key, is_active=True).first()
        if device is None:
            return Response({"detail": "Μη έγκυρο ή ανενεργό api_key."}, status=403)

        serializer = ReadingInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        temperature = serializer.validated_data["temperature"]
        humidity = serializer.validated_data["humidity"]
        created_at = serializer.validated_data.get("timestamp", timezone.now())

        reading, risk_level = record_reading(device, temperature, humidity, created_at)

        return Response(
            {
                "stored": True,
                "signal_level": reading.signal_level,
                "severity": reading.severity,
                "message": risk_level.message if risk_level else "",
                "work_break_schedule": risk_level.work_break_schedule if risk_level else "",
            },
            status=201,
        )


def _parse_ecowitt_timestamp(raw):
    """Η Ecowitt στέλνει dateutc σαν 'YYYY-MM-DD HH:MM:SS' σε UTC."""
    if not raw:
        return timezone.now()
    try:
        naive = datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return timezone.make_aware(naive, datetime.timezone.utc)
    except ValueError:
        return timezone.now()


class EcowittIngestView(APIView):
    """
    POST /api/ecowitt/
    Δέχεται δεδομένα ΑΠΕΥΘΕΙΑΣ από Ecowitt Gateway (GW1100/GW1000/GW2000),
    ρυθμισμένο σαν "Customized" server στην εφαρμογή WS View Plus, με τύπο
    πρωτοκόλλου "Ecowitt" (POST, x-www-form-urlencoded). Καμία X-API-Key εδώ -
    η ταυτοποίηση γίνεται μέσω του PASSKEY που στέλνει το ίδιο το Gateway.

    Μία μοναδική request μπορεί να περιέχει δεδομένα από πολλά κανάλια/
    αισθητήρες ταυτόχρονα:
      - tempf / humidity          -> κύριος αισθητήρας (WN32/WH32)
      - temp1f/humidity1 ... temp8f/humidity8 -> πολυκάναλο WH31 (κανάλια 1-8)

    Για κάθε Device που έχει καταχωρημένο το ίδιο ecowitt_passkey, διαβάζουμε
    το σωστό ζευγάρι πεδίων ανάλογα με το ecowitt_channel του (ή tempf/humidity
    αν το ecowitt_channel είναι κενό), και τρέχουμε το ίδιο pipeline
    αξιολόγησης/ειδοποίησης με το /api/ingest/.

    Πάντα επιστρέφει HTTP 200 - το Gateway δεν διαβάζει το σώμα της απάντησης,
    απλά περιμένει επιβεβαίωση παραλαβής.
    """

    def post(self, request):
        return self._handle(request)

    def get(self, request):
        return self._handle(request)

    def _handle(self, request):
        # Δεν ξέρουμε σίγουρα αν το Gateway σου θα στείλει GET ή POST (εξαρτάται
        # από τη ρύθμιση στην εφαρμογή WS View Plus) - δεχόμαστε και τα δύο, και
        # διαβάζουμε τιμές είτε από query params είτε από το σώμα του request.
        data = {**request.query_params.dict(), **request.data}
        passkey = data.get("PASSKEY") or data.get("passkey")
        if not passkey:
            return Response({"detail": "Λείπει το PASSKEY."}, status=200)

        devices = Device.objects.filter(ecowitt_passkey=passkey, is_active=True)
        if not devices:
            logger.info("Ecowitt: άγνωστο PASSKEY '%s'. Πλήρες μήνυμα που ελήφθη: %s", passkey, dict(data))
            return Response({"detail": "Άγνωστο PASSKEY - δεν βρέθηκε συσκευή με αυτό το ecowitt_passkey."}, status=200)

        timestamp = _parse_ecowitt_timestamp(data.get("dateutc"))
        processed = []

        for device in devices:
            if device.ecowitt_channel:
                temp_f = data.get(f"temp{device.ecowitt_channel}f")
                humidity_raw = data.get(f"humidity{device.ecowitt_channel}")
            else:
                temp_f = data.get("tempf")
                humidity_raw = data.get("humidity")

            if temp_f is None or humidity_raw is None:
                logger.info(
                    "Ecowitt: η συσκευή '%s' (κανάλι %s) δεν βρέθηκε σε αυτό το μήνυμα. Πεδία που ήρθαν: %s",
                    device.name, device.ecowitt_channel or "κύριο", list(data.keys()),
                )
                continue  # αυτό το κανάλι δεν ήταν μέσα σε αυτή τη μέτρηση

            try:
                temperature_c = round((float(temp_f) - 32) * 5 / 9, 1)
                humidity = float(humidity_raw)
            except (TypeError, ValueError):
                continue

            record_reading(device, temperature_c, humidity, timestamp)
            processed.append(device.name)

        return Response({"stored": True, "devices": processed}, status=200)


class DeviceListView(APIView):
    """GET /api/devices/  -> όλες οι συσκευές + τρέχουσα κατάσταση (χρησιμοποιείται και για τις καρτέλες)."""

    def get(self, request):
        devices = Device.objects.filter(is_active=True).order_by("name")
        return Response(DeviceSerializer(devices, many=True).data)


class DeviceReadingsView(APIView):
    """GET /api/devices/<id>/readings/?minutes=120 -> μετρήσεις για το γράφημα."""

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
    return render(request, "monitor/dashboard.html")


def thresholds_page(request):
    return render(request, "monitor/thresholds.html")


class RiskLevelListView(generics.ListAPIView):
    """GET /api/risk-levels/ -> οι 5 σταθερές βαθμίδες (πρόγραμμα/μήνυμα/notify)."""
    queryset = RiskLevel.objects.order_by("level_number")
    serializer_class = RiskLevelSerializer


class RiskLevelDetailView(generics.RetrieveUpdateAPIView):
    """PATCH /api/risk-levels/<id>/ -> άλλαξε πρόγραμμα διαλείμματος / μήνυμα / notify."""
    queryset = RiskLevel.objects.all()
    serializer_class = RiskLevelSerializer


class HeatIndexRowListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/heat-table/  -> όλες οι γραμμές του πίνακα (μία ανά θερμοκρασία)
    POST /api/heat-table/  -> πρόσθεσε νέα γραμμή θερμοκρασίας
    """
    queryset = HeatIndexRow.objects.order_by("temperature")
    serializer_class = HeatIndexRowSerializer


class HeatIndexRowDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH/DELETE /api/heat-table/<id>/ -> επεξεργασία ή διαγραφή μιας γραμμής."""
    queryset = HeatIndexRow.objects.all()
    serializer_class = HeatIndexRowSerializer


class LoadModerateTableView(APIView):
    """
    POST /api/heat-table/load-moderate/
    Αντικαθιστά ΟΛΟΚΛΗΡΟ τον πίνακα θερμοκρασίας/υγρασίας με τον πίνακα
    "Μέτρια εργασία". Ο χρήστης μπορεί μετά να προσαρμόσει οποιαδήποτε γραμμή.
    """

    def post(self, request):
        HeatIndexRow.objects.all().delete()
        HeatIndexRow.objects.bulk_create([
            HeatIndexRow(
                temperature=row[0], max_humidity_level1=row[1],
                max_humidity_level2=row[2], max_humidity_level3=row[3], max_humidity_level4=row[4],
            )
            for row in MODERATE_WORK_TABLE
        ])
        rows = HeatIndexRow.objects.order_by("temperature")
        return Response(HeatIndexRowSerializer(rows, many=True).data)
