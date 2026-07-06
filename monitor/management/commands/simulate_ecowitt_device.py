import random
import time

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from monitor.models import Device


class Command(BaseCommand):
    help = (
        "Προσομοιώνει ένα Ecowitt Gateway που στέλνει δεδομένα στο /api/ecowitt/, "
        "χρησιμοποιώντας το ecowitt_passkey μιας υπαρκτής συσκευής σου. Χρήσιμο για να "
        "δεις ζωντανά το dashboard/SMS να αντιδρούν, χωρίς πραγματικό Gateway."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "device_id", type=int,
            help="Το ID της συσκευής (δες τη λίστα στο /admin/monitor/device/). Πρέπει να έχει ήδη ecowitt_passkey.",
        )
        parser.add_argument("--url", default="http://127.0.0.1:8000/api/ecowitt/")
        parser.add_argument("--interval", type=int, default=10, help="δευτερόλεπτα ανάμεσα σε μετρήσεις")
        parser.add_argument("--count", type=int, default=0, help="0 = επ' άπειρον")
        parser.add_argument(
            "--ramp-to-danger", action="store_true",
            help="Αν ενεργό, ανεβάζει σταδιακά τη θερμοκρασία μέχρι το πιο επικίνδυνο επίπεδο, ώστε να δοκιμάσεις SMS.",
        )

    def handle(self, *args, **options):
        try:
            device = Device.objects.get(id=options["device_id"])
        except Device.DoesNotExist:
            raise CommandError(f"Δεν βρέθηκε συσκευή με id={options['device_id']}")

        if not device.ecowitt_passkey:
            raise CommandError(
                f"Η συσκευή '{device.name}' δεν έχει ecowitt_passkey. "
                "Πρόσθεσέ το στο admin πρώτα (ή βάλε ένα οποιοδήποτε δοκιμαστικό, π.χ. 'TEST-PASSKEY-123')."
            )

        temp_c = 30.0
        humidity = 55.0
        ramp = options["ramp_to_danger"]
        i = 0

        self.stdout.write(f"Προσομοίωση Ecowitt Gateway για τη συσκευή '{device.name}' (passkey={device.ecowitt_passkey})")

        while True:
            if ramp:
                # ανεβάζει σταδιακά προς το πιο ζεστό/επικίνδυνο άκρο του πίνακα
                temp_c = min(46.0, temp_c + 1.5)
                humidity = min(90.0, humidity + 3)
            else:
                temp_c += random.uniform(-1, 1)
                humidity += random.uniform(-3, 3)
                temp_c = max(20, min(46, temp_c))
                humidity = max(20, min(95, humidity))

            temp_f = temp_c * 9 / 5 + 32
            payload = {
                "PASSKEY": device.ecowitt_passkey,
                "stationtype": "GW1100A_V2.0.0",
                "model": "GW1100",
                "dateutc": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            if device.ecowitt_channel:
                payload[f"temp{device.ecowitt_channel}f"] = round(temp_f, 1)
                payload[f"humidity{device.ecowitt_channel}"] = round(humidity)
            else:
                payload["tempf"] = round(temp_f, 1)
                payload["humidity"] = round(humidity)

            try:
                resp = requests.post(options["url"], data=payload, timeout=5)
                body = resp.json()
                if body.get("detail"):
                    self.stdout.write(self.style.ERROR(
                        f"{temp_c:.1f}°C / {humidity:.0f}% -> ΠΡΟΒΛΗΜΑ: {body['detail']}"
                    ))
                elif body.get("stored") and not body.get("devices"):
                    self.stdout.write(self.style.WARNING(
                        f"{temp_c:.1f}°C / {humidity:.0f}% -> Το PASSKEY βρέθηκε, ΑΛΛΑ καμία "
                        "συσκευή δεν ταίριαξε (λάθος ecowitt_channel;). Τίποτα δεν αποθηκεύτηκε."
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"{temp_c:.1f}°C ({temp_f:.1f}°F) / {humidity:.0f}% -> "
                        f"OK, αποθηκεύτηκε για: {', '.join(body.get('devices', []))}"
                    ))
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"Request failed: {exc}"))

            i += 1
            if options["count"] and i >= options["count"]:
                break
            if ramp and temp_c >= 46.0:
                self.stdout.write(self.style.SUCCESS("Έφτασε στο πιο ζεστό σημείο του πίνακα. Σταματάει."))
                break
            time.sleep(options["interval"])