import random
import time

import requests
from django.core.management.base import BaseCommand, CommandError

from monitor.models import Device


class Command(BaseCommand):
    help = (
        "Creates (if needed) a demo device and posts temperature/humidity readings "
        "to the ingest API every few seconds, so you can see the dashboard update "
        "without real hardware."
    )

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Demo Sensor", help="Όνομα συσκευής (δημιουργείται αν δεν υπάρχει).")
        parser.add_argument("--device-id", type=int, default=None, help="Εναλλακτικά, χρησιμοποίησε υπαρκτή συσκευή by ID αντί για --name.")
        parser.add_argument("--url", default="http://127.0.0.1:8000/api/ingest/")
        parser.add_argument("--interval", type=int, default=10, help="δευτερόλεπτα ανάμεσα σε μετρήσεις")
        parser.add_argument("--count", type=int, default=0, help="0 = επ' άπειρον")
        parser.add_argument(
            "--ramp-to-danger", action="store_true",
            help="Αν ενεργό, ανεβάζει σταδιακά τη θερμοκρασία μέχρι το πιο επικίνδυνο σημείο, ώστε να δοκιμάσεις SMS.",
        )

    def handle(self, *args, **options):
        if options["device_id"]:
            try:
                device = Device.objects.get(id=options["device_id"])
            except Device.DoesNotExist:
                raise CommandError(f"Δεν βρέθηκε συσκευή με id={options['device_id']}")
        else:
            device, _ = Device.objects.get_or_create(
                name=options["name"], defaults={"location": "Simulation"}
            )

        self.stdout.write(f"Χρήση συσκευής '{device.name}' (api_key={device.api_key})")

        temp, humidity = 26.0, 55.0
        ramp = options["ramp_to_danger"]
        i = 0

        while True:
            if ramp:
                temp = min(46.0, temp + 1.5)
                humidity = min(90.0, humidity + 3)
            else:
                temp += random.uniform(-1.5, 1.5)
                humidity += random.uniform(-3, 3)
                temp = max(10, min(45, temp))
                humidity = max(10, min(100, humidity))

            try:
                resp = requests.post(
                    options["url"],
                    json={"temperature": round(temp, 1), "humidity": round(humidity, 1)},
                    headers={"X-API-Key": device.api_key},
                    timeout=5,
                )
                body = resp.json()
                if body.get("signal_level"):
                    self.stdout.write(self.style.SUCCESS(
                        f"{temp:.1f}°C {humidity:.1f}% -> OK, {body['signal_level']}"
                    ))
                else:
                    self.stdout.write(f"{temp:.1f}°C {humidity:.1f}% -> {resp.status_code} {body}")
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"Request failed: {exc}"))

            i += 1
            if options["count"] and i >= options["count"]:
                break
            if ramp and temp >= 46.0:
                self.stdout.write(self.style.SUCCESS("Έφτασε στο πιο ζεστό σημείο. Σταματάει."))
                break
            time.sleep(options["interval"])