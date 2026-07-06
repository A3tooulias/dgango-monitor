import math
import random

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from monitor.models import Device, Reading
from monitor.services import evaluate_reading


class Command(BaseCommand):
    help = (
        "Γεμίζει ΑΜΕΣΩΣ το ιστορικό μιας συσκευής με ρεαλιστικά δοκιμαστικά δεδομένα "
        "(καμπύλη θερμοκρασίας/υγρασίας τις τελευταίες ώρες), ώστε να δεις αμέσως το "
        "γράφημα στην αρχική σελίδα να δουλεύει. ΔΕΝ στέλνει κανένα SMS - σκόπιμα, ώστε "
        "να μη σε πλημμυρίσει με δοκιμαστικές ειδοποιήσεις ενώ η καμπύλη διασχίζει επίπεδα."
    )

    def add_arguments(self, parser):
        parser.add_argument("device_id", type=int, help="Το ID της συσκευής (δες /admin/monitor/device/).")
        parser.add_argument("--hours", type=int, default=2, help="Πόσες ώρες ιστορικού να δημιουργηθούν (προεπιλογή 2).")
        parser.add_argument("--interval-minutes", type=int, default=5, help="Απόσταση ανάμεσα σε μετρήσεις (προεπιλογή 5).")
        parser.add_argument("--peak-temp", type=float, default=38.0, help="Η πιο ζεστή τιμή της καμπύλης (°C).")
        parser.add_argument("--base-temp", type=float, default=27.0, help="Η πιο δροσερή τιμή της καμπύλης (°C).")

    def handle(self, *args, **options):
        try:
            device = Device.objects.get(id=options["device_id"])
        except Device.DoesNotExist:
            raise CommandError(f"Δεν βρέθηκε συσκευή με id={options['device_id']}")

        hours = options["hours"]
        interval = options["interval_minutes"]
        base_temp = options["base_temp"]
        peak_temp = options["peak_temp"]
        count = max(1, int(hours * 60 / interval))
        now = timezone.now()
        amplitude = (peak_temp - base_temp) / 2
        midpoint = base_temp + amplitude

        last_reading = None
        created = 0

        for i in range(count, -1, -1):
            ts = now - timezone.timedelta(minutes=i * interval)
            progress = (count - i) / count  # 0 -> 1 καθώς πλησιάζουμε το τώρα

            # ήπια καμπύλη πάνω-κάτω (σαν μια ζεστή μέρα) + λίγος τυχαίος θόρυβος
            temp = round(midpoint + amplitude * math.sin(progress * math.pi) + random.uniform(-0.6, 0.6), 1)
            humidity = round(60 - 18 * math.sin(progress * math.pi) + random.uniform(-3, 3))
            humidity = max(20, min(95, humidity))

            risk_level = evaluate_reading(temp, humidity)
            signal_level = f"Επίπεδο {risk_level.level_number}" if risk_level else "Χωρίς πίνακα ορίων ακόμα"
            severity = risk_level.level_number if risk_level else 0

            last_reading = Reading.objects.create(
                device=device, temperature=temp, humidity=humidity,
                signal_level=signal_level, severity=severity, matched_level=risk_level,
                created_at=ts,
            )
            created += 1

        if last_reading:
            device.last_seen = last_reading.created_at
            device.last_temperature = last_reading.temperature
            device.last_humidity = last_reading.humidity
            device.last_signal_level = last_reading.signal_level
            device.last_severity = last_reading.severity
            device.save(update_fields=[
                "last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity",
            ])

        self.stdout.write(self.style.SUCCESS(
            f"Έτοιμο. Δημιουργήθηκαν {created} δοκιμαστικές μετρήσεις για '{device.name}' "
            f"({hours} ώρες, κάθε {interval} λεπτά). Κανένα SMS δεν στάλθηκε."
        ))