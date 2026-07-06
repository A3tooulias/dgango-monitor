from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0005_recipient_devices"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="ecowitt_passkey",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="device",
            name="ecowitt_channel",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
