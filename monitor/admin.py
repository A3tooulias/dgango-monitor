from django.contrib import admin

from .models import Device, NotificationLog, Reading, Recipient, ThresholdRule


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "location", "is_active", "is_online", "last_seen", "last_temperature", "last_humidity", "last_signal_level", "api_key"]
    readonly_fields = ["api_key", "last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity"]


@admin.register(ThresholdRule)
class ThresholdRuleAdmin(admin.ModelAdmin):
    list_display = ["severity", "name", "min_temperature", "max_temperature", "min_humidity", "max_humidity", "work_break_schedule", "notify"]
    list_display_links = ["name"]
    list_editable = ["severity"]
    ordering = ["severity"]


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ["device", "temperature", "humidity", "signal_level", "severity", "created_at"]
    list_filter = ["device", "signal_level"]
    date_hierarchy = "created_at"


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ["name", "phone_number", "viber_user_id", "receive_sms", "receive_viber", "is_active"]


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "device", "signal_level", "channel", "recipient", "success"]
    list_filter = ["channel", "success", "signal_level"]
