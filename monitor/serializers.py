from rest_framework import serializers

from .models import Device, HeatIndexRow, Reading, RiskLevel


class ReadingInSerializer(serializers.Serializer):
    """What a sensor device POSTs to /api/ingest/."""

    temperature = serializers.FloatField()
    humidity = serializers.FloatField(min_value=0, max_value=100)
    timestamp = serializers.DateTimeField(required=False)


class ReadingOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        fields = ["id", "temperature", "humidity", "signal_level", "severity", "created_at"]


class DeviceSerializer(serializers.ModelSerializer):
    is_online = serializers.BooleanField(read_only=True)
    last_message = serializers.SerializerMethodField()
    last_schedule = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id", "name", "location", "is_active", "is_online",
            "last_seen", "last_temperature", "last_humidity", "last_signal_level",
            "last_severity", "last_message", "last_schedule",
        ]

    def _latest_level(self, device):
        latest = device.readings.select_related("matched_level").first()
        return latest.matched_level if latest else None

    def get_last_message(self, device):
        level = self._latest_level(device)
        return level.message if level else "Δεν υπάρχουν ακόμα μετρήσεις."

    def get_last_schedule(self, device):
        level = self._latest_level(device)
        return level.work_break_schedule if level else "—"


class RiskLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskLevel
        fields = ["id", "level_number", "work_break_schedule", "message", "notify"]
        read_only_fields = ["level_number"]


class HeatIndexRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeatIndexRow
        fields = [
            "id", "temperature",
            "max_humidity_level1", "max_humidity_level2",
            "max_humidity_level3", "max_humidity_level4",
        ]
