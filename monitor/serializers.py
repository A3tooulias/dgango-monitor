from rest_framework import serializers

from .models import Device, Reading, ThresholdRule


class ThresholdRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdRule
        fields = [
            "id", "name", "severity",
            "min_temperature", "max_temperature",
            "min_humidity", "max_humidity",
            "work_break_schedule", "message", "notify",
        ]


class ReadingInSerializer(serializers.Serializer):
    """What a sensor device POSTs to /api/ingest/."""

    temperature = serializers.FloatField()
    humidity = serializers.FloatField(min_value=0, max_value=100)
    # optional: device can send its own timestamp; otherwise server time is used
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

    def _latest_rule(self, device):
        latest = device.readings.select_related("matched_rule").first()
        return latest.matched_rule if latest else None

    def get_last_message(self, device):
        rule = self._latest_rule(device)
        return rule.message if rule else "Conditions normal."

    def get_last_schedule(self, device):
        rule = self._latest_rule(device)
        return rule.work_break_schedule if rule else "Normal schedule"
