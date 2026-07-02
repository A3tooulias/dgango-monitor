import random
import time

import requests
from django.core.management.base import BaseCommand

from monitor.models import Device


class Command(BaseCommand):
    help = (
        "Creates (if needed) a demo device and posts random temperature/humidity "
        "readings to the ingest API every few seconds, so you can see the "
        "dashboard update without real hardware."
    )

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Demo Sensor")
        parser.add_argument("--url", default="http://127.0.0.1:8000/api/ingest/")
        parser.add_argument("--interval", type=int, default=10, help="seconds between readings")
        parser.add_argument("--count", type=int, default=0, help="0 = run forever")

    def handle(self, *args, **options):
        device, _ = Device.objects.get_or_create(
            name=options["name"], defaults={"location": "Simulation"}
        )
        self.stdout.write(f"Using device '{device.name}' (api_key={device.api_key})")

        temp, humidity = 26.0, 55.0
        i = 0
        while True:
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
                self.stdout.write(f"{temp:.1f}°C {humidity:.1f}% -> {resp.status_code} {resp.json()}")
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"Request failed: {exc}"))

            i += 1
            if options["count"] and i >= options["count"]:
                break
            time.sleep(options["interval"])
