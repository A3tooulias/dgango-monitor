"""
Το πραγματικό "poll" του AgroMet - ξεχωριστό από το πώς καλείται (χειροκίνητα
μέσω management command, ή αυτόματα μέσω του in-process scheduler), ώστε να
μην υπάρχει διπλός κώδικας.
"""
import logging

import requests
from django.db import close_old_connections
from django.utils import timezone

from .agromet import AGROMET_XML_URL, find_nearest_station, parse_agromet_observations

logger = logging.getLogger(__name__)


def run_agromet_poll():
    """
    Τραβάει τρέχουσες μετρήσεις από το AgroMet και τις καταγράφει για κάθε
    συσκευή που έχει ρυθμισμένο worksite_address/latitude/longitude.
    Επιστρέφει μια λίστα από (επίπεδο log, μήνυμα) - χρησιμοποιείται είτε από
    το management command (τυπώνει στην κονσόλα), είτε από τον αυτόματο
    scheduler (γράφει στο logs/app.log).
    """
    # Ασφαλές να καλείται από background thread (ο scheduler τρέχει σε δικό
    # του thread, όχι στο κύριο request/response κύκλωμα) - κλείνει τυχόν
    # "μπαγιάτικες" συνδέσεις βάσης πριν ξεκινήσει.
    close_old_connections()

    from .models import Device, StationObservation  # lazy import - αποφεύγει προβλήματα φόρτωσης apps
    from .services import evaluate_reading, record_reading

    results = []

    try:
        response = requests.get(AGROMET_XML_URL, timeout=15)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        results.append(("error", f"Αποτυχία λήψης δεδομένων από το AgroMet: {exc}"))
        return results

    try:
        observations = parse_agromet_observations(response.text)
    except Exception as exc:  # noqa: BLE001
        results.append(("error", f"Αποτυχία ανάγνωσης XML: {exc}"))
        return results

    # Αποθηκεύουμε ΟΛΕΣ τις μετρήσεις (όχι μόνο των δικών μας συσκευών) στη
    # ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ (όχι σε Django cache - το poll τρέχει σε ξεχωριστή
    # διεργασία από τον server, και το cache είναι ανά διεργασία, άρα δεν θα
    # το έβλεπε ποτέ ο server). Η βάση όμως μοιράζεται κανονικά μεταξύ τους.
    for code, data in observations.items():
        StationObservation.objects.update_or_create(
            station_code=code,
            defaults={
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
                "observed_at": data.get("date_time") or "",
            },
        )

    devices = Device.objects.filter(
        is_active=True, data_source="agromet",
        worksite_latitude__isnull=False, worksite_longitude__isnull=False,
    )
    if not devices:
        results.append(("info", "Καμία συσκευή δεν έχει ρυθμισμένο worksite address ακόμα."))
        return results

    for device in devices:
        station_code, distance_km = find_nearest_station(
            device.worksite_latitude, device.worksite_longitude
        )
        data = observations.get(station_code)

        if not data or data["temperature"] is None or data["humidity"] is None:
            results.append((
                "warning",
                f"{device.name}: ο πλησιέστερος σταθμός ({station_code}, {distance_km:.1f} km) "
                "δεν έχει έγκυρη θερμοκρασία/υγρασία αυτή τη στιγμή.",
            ))
            continue

        if device.agromet_station_code != station_code:
            device.agromet_station_code = station_code
            device.save(update_fields=["agromet_station_code"])

        temperature = data["temperature"]
        humidity = data["humidity"]
        risk_level = evaluate_reading(temperature, humidity)
        label = f"Επίπεδο {risk_level.level_number}" if risk_level else "Χωρίς πίνακα ορίων ακόμα"

        try:
            record_reading(device, temperature, humidity)
        except TypeError:
            record_reading(device, temperature, humidity, timezone.now())

        results.append((
            "success",
            f"{device.name}: σταθμός {station_code} ({distance_km:.1f} km) -> "
            f"{temperature}°C / {humidity}% -> {label}",
        ))

    return results