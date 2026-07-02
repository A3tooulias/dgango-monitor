from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0001_initial"),
    ]

    operations = [
        # ThresholdRule: priority -> severity, drop the fixed enum, message/notify text now optional
        migrations.RemoveField(model_name="thresholdrule", name="priority"),
        migrations.RemoveField(model_name="thresholdrule", name="signal_level"),
        migrations.AddField(
            model_name="thresholdrule",
            name="severity",
            field=models.PositiveIntegerField(
                default=1,
                help_text="1 = ασφαλέστερο επίπεδο, μεγαλύτερος αριθμός = πιο επικίνδυνο.",
            ),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="name",
            field=models.CharField(help_text='e.g. "Επίπεδο 3 - Μισή ώρα διάλειμμα"', max_length=100),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="message",
            field=models.CharField(
                blank=True,
                help_text="Κείμενο που στέλνεται στο Viber/SMS όταν ενεργοποιείται αυτό το επίπεδο.",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="min_temperature",
            field=models.FloatField(blank=True, help_text="°C, κενό = χωρίς κάτω όριο", null=True),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="max_temperature",
            field=models.FloatField(blank=True, help_text="°C, κενό = χωρίς άνω όριο", null=True),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="min_humidity",
            field=models.FloatField(blank=True, help_text="%, κενό = χωρίς κάτω όριο", null=True),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="max_humidity",
            field=models.FloatField(blank=True, help_text="%, κενό = χωρίς άνω όριο", null=True),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="work_break_schedule",
            field=models.CharField(
                blank=True,
                help_text='π.χ. "15 λεπτά διάλειμμα ανά ώρα" ή "Απαγόρευση εργασίας"',
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="thresholdrule",
            name="notify",
            field=models.BooleanField(default=True, help_text="Αποστολή ειδοποίησης Viber/SMS σε αυτό το επίπεδο;"),
        ),
        migrations.AlterModelOptions(
            name="thresholdrule",
            options={"ordering": ["severity"]},
        ),
        # Device: widen last_signal_level, add last_severity cache
        migrations.AlterField(
            model_name="device",
            name="last_signal_level",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="device",
            name="last_severity",
            field=models.IntegerField(blank=True, null=True),
        ),
        # Reading: widen signal_level, add severity
        migrations.AlterField(
            model_name="reading",
            name="signal_level",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="reading",
            name="severity",
            field=models.IntegerField(blank=True, null=True),
        ),
        # NotificationLog: widen signal_level
        migrations.AlterField(
            model_name="notificationlog",
            name="signal_level",
            field=models.CharField(max_length=100),
        ),
    ]
