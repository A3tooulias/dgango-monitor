from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0002_flexible_severity_levels"),
    ]

    operations = [
        migrations.RemoveField(model_name="recipient", name="viber_user_id"),
        migrations.RemoveField(model_name="recipient", name="receive_viber"),
        migrations.AlterField(
            model_name="notificationlog",
            name="channel",
            field=models.CharField(default="sms", max_length=20),
        ),
    ]
