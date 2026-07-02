import secrets

from django.db import models
from django.utils import timezone


def generate_api_key():
    return secrets.token_hex(20)


class Device(models.Model):
    """A physical WiFi temperature/humidity sensor (ESP32, Lascar EL-WiFi, etc.)."""

    name = models.CharField(max_length=100)
    location = models.CharField(max_length=150, blank=True)
    api_key = models.CharField(max_length=64, unique=True, default=generate_api_key, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # cached fields updated on every reading, so the dashboard doesn't have
    # to hit the Reading table just to show "current status"
    last_seen = models.DateTimeField(null=True, blank=True)
    last_temperature = models.FloatField(null=True, blank=True)
    last_humidity = models.FloatField(null=True, blank=True)
    last_signal_level = models.CharField(max_length=100, blank=True)
    last_severity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.location})" if self.location else self.name

    @property
    def is_online(self):
        from django.conf import settings

        if not self.last_seen:
            return False
        cutoff = timezone.now() - timezone.timedelta(minutes=settings.DEVICE_OFFLINE_AFTER_MINUTES)
        return self.last_seen >= cutoff


class ThresholdRule(models.Model):
    """
    One row of YOUR array / risk level. Each rule defines a temperature and
    humidity window plus what should happen when a reading falls inside it
    (e.g. "15 min break every hour", or "stop work").

    Levels are fully user-defined: add as many as you like from the web UI
    (Settings -> Thresholds) or the Django admin. `severity` controls both
    display order and evaluation order - the HIGHEST severity whose range
    matches a reading wins, so if two ranges overlap the more dangerous one
    takes priority.
    """

    name = models.CharField(max_length=100, help_text='e.g. "Επίπεδο 3 - Μισή ώρα διάλειμμα"')
    severity = models.PositiveIntegerField(
        default=1,
        help_text="1 = ασφαλέστερο επίπεδο, μεγαλύτερος αριθμός = πιο επικίνδυνο.",
    )

    min_temperature = models.FloatField(null=True, blank=True, help_text="°C, κενό = χωρίς κάτω όριο")
    max_temperature = models.FloatField(null=True, blank=True, help_text="°C, κενό = χωρίς άνω όριο")
    min_humidity = models.FloatField(null=True, blank=True, help_text="%, κενό = χωρίς κάτω όριο")
    max_humidity = models.FloatField(null=True, blank=True, help_text="%, κενό = χωρίς άνω όριο")

    work_break_schedule = models.CharField(
        max_length=100,
        blank=True,
        help_text='π.χ. "15 λεπτά διάλειμμα ανά ώρα" ή "Απαγόρευση εργασίας"',
    )
    message = models.CharField(
        max_length=255,
        blank=True,
        help_text="Κείμενο που στέλνεται στο Viber/SMS όταν ενεργοποιείται αυτό το επίπεδο.",
    )
    notify = models.BooleanField(default=True, help_text="Αποστολή ειδοποίησης Viber/SMS σε αυτό το επίπεδο;")

    class Meta:
        ordering = ["severity"]

    def __str__(self):
        return f"[σοβαρότητα {self.severity}] {self.name}"

    def matches(self, temperature, humidity):
        if self.min_temperature is not None and temperature < self.min_temperature:
            return False
        if self.max_temperature is not None and temperature > self.max_temperature:
            return False
        if self.min_humidity is not None and humidity < self.min_humidity:
            return False
        if self.max_humidity is not None and humidity > self.max_humidity:
            return False
        return True


class Reading(models.Model):
    """A single temperature/humidity data point coming in from a device."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="readings")
    temperature = models.FloatField(help_text="Degrees Celsius")
    humidity = models.FloatField(help_text="Relative humidity %")
    signal_level = models.CharField(max_length=100, blank=True)
    severity = models.IntegerField(null=True, blank=True)
    matched_rule = models.ForeignKey(ThresholdRule, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["device", "created_at"])]

    def __str__(self):
        return f"{self.device.name}: {self.temperature}°C / {self.humidity}% @ {self.created_at:%Y-%m-%d %H:%M}"


class Recipient(models.Model):
    """Someone who should get Viber/SMS alerts."""

    name = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=32, blank=True, help_text="E.164 format for SMS, e.g. +35799123456"
    )
    viber_user_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Viber user ID obtained once this person messages your Viber bot",
    )
    receive_sms = models.BooleanField(default=True)
    receive_viber = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class NotificationLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="notifications")
    signal_level = models.CharField(max_length=100)
    message = models.CharField(max_length=255)
    channel = models.CharField(max_length=20)  # 'viber' or 'sms'
    recipient = models.ForeignKey(Recipient, on_delete=models.SET_NULL, null=True)
    success = models.BooleanField(default=False)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.device.name} -> {self.channel}:{self.recipient} [{self.signal_level}]"
