import django.db.models.deletion
from django.db import migrations, models


def create_five_empty_levels(apps, schema_editor):
    """
    Δημιουργεί μόνο τις 5 ΓΡΑΜΜΕΣ (level_number 1-5) ώστε να υπάρχει κάτι να
    επεξεργαστείς στη σελίδα /thresholds/. Δεν γεμίζει κείμενο/προγράμματα -
    αυτά τα ορίζεις εσύ.
    """
    RiskLevel = apps.get_model("monitor", "RiskLevel")
    for n in range(1, 6):
        RiskLevel.objects.get_or_create(level_number=n)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0003_sms_only"),
    ]

    operations = [
        migrations.RemoveField(model_name="reading", name="matched_rule"),
        migrations.DeleteModel(name="ThresholdRule"),

        migrations.CreateModel(
            name="RiskLevel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level_number", models.PositiveSmallIntegerField(unique=True)),
                ("work_break_schedule", models.CharField(blank=True, max_length=100)),
                ("message", models.CharField(blank=True, max_length=255)),
                ("notify", models.BooleanField(default=True)),
            ],
            options={"ordering": ["level_number"]},
        ),
        migrations.CreateModel(
            name="HeatIndexRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("temperature", models.IntegerField(unique=True)),
                ("max_humidity_level1", models.FloatField()),
                ("max_humidity_level2", models.FloatField()),
                ("max_humidity_level3", models.FloatField()),
                ("max_humidity_level4", models.FloatField()),
            ],
            options={"ordering": ["temperature"]},
        ),
        migrations.AddField(
            model_name="reading",
            name="matched_level",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="monitor.risklevel"),
        ),

        migrations.RunPython(create_five_empty_levels, noop_reverse),
    ]
