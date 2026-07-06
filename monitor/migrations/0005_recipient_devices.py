from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0004_fixed_risk_levels"),
    ]

    operations = [
        migrations.AddField(
            model_name="recipient",
            name="devices",
            field=models.ManyToManyField(blank=True, related_name="recipients", to="monitor.device"),
        ),
    ]
