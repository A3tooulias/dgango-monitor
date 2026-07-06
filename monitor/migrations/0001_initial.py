import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion

import monitor.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Device",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("location", models.CharField(blank=True, max_length=150)),
                ("api_key", models.CharField(default=monitor.models.generate_api_key, editable=False, max_length=64, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(blank=True, null=True)),
                ("last_temperature", models.FloatField(blank=True, null=True)),
                ("last_humidity", models.FloatField(blank=True, null=True)),
                ("last_signal_level", models.CharField(blank=True, max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name="ThresholdRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("priority", models.PositiveIntegerField(default=100)),
                ("min_temperature", models.FloatField(blank=True, help_text="°C, leave blank for no lower bound", null=True)),
                ("max_temperature", models.FloatField(blank=True, help_text="°C, leave blank for no upper bound", null=True)),
                ("min_humidity", models.FloatField(blank=True, help_text="%, leave blank for no lower bound", null=True)),
                ("max_humidity", models.FloatField(blank=True, help_text="%, leave blank for no upper bound", null=True)),
                ("signal_level", models.CharField(choices=[("SAFE", "Safe - continue working"), ("CAUTION", "Caution - increase water breaks"), ("WARNING", "Warning - scheduled rest breaks"), ("DANGER", "Danger - stop work")], default="SAFE", max_length=20)),
                ("work_break_schedule", models.CharField(blank=True, help_text='e.g. "45 min work / 15 min rest" or "STOP WORK IMMEDIATELY"', max_length=100)),
                ("message", models.CharField(help_text="Text sent in the Viber/SMS alert when this rule triggers.", max_length=255)),
                ("notify", models.BooleanField(default=True, help_text="Send a Viber/SMS alert when this rule triggers?")),
            ],
            options={"ordering": ["priority"]},
        ),
        migrations.CreateModel(
            name="Recipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("phone_number", models.CharField(blank=True, help_text="E.164 format for SMS, e.g. +35799123456", max_length=32)),
                ("viber_user_id", models.CharField(blank=True, help_text="Viber user ID obtained once this person messages your Viber bot", max_length=64)),
                ("receive_sms", models.BooleanField(default=True)),
                ("receive_viber", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Reading",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("temperature", models.FloatField(help_text="Degrees Celsius")),
                ("humidity", models.FloatField(help_text="Relative humidity %")),
                ("signal_level", models.CharField(blank=True, max_length=20)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="readings", to="monitor.device")),
                ("matched_rule", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="monitor.thresholdrule")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="reading",
            index=models.Index(fields=["device", "created_at"], name="monitor_rea_device__1e1d0a_idx"),
        ),
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("signal_level", models.CharField(max_length=20)),
                ("message", models.CharField(max_length=255)),
                ("channel", models.CharField(max_length=20)),
                ("success", models.BooleanField(default=False)),
                ("error", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="monitor.device")),
                ("recipient", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="monitor.recipient")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
