"""
Επιχειρησιακή λογική:
  1. evaluate_reading()  -> βρίσκει σε ποιο Επίπεδο (1-5) ανήκει μια μέτρηση,
                             κοιτώντας τον πίνακα θερμοκρασίας/υγρασίας (HeatIndexRow).
  2. maybe_notify()      -> αποφασίζει αν πρέπει να σταλεί SMS τώρα, και το στέλνει.
  3. send_sms()          -> wrapper γύρω από το SMSGate API (sms-gate.app).
"""
import logging

import requests
from django.conf import settings
from django.utils import timezone

from .models import HeatIndexRow, NotificationLog, Reading, RiskLevel

logger = logging.getLogger(__name__)


def evaluate_reading(temperature, humidity):
    """
    Ψάχνει στον πίνακα HeatIndexRow (τη σελίδα /thresholds/) ποιο Επίπεδο
    (1-5) αντιστοιχεί σε αυτή τη θερμοκρασία/υγρασία, και επιστρέφει το
    αντίστοιχο RiskLevel. Αν δεν υπάρχει καθόλου πίνακας ακόμα, επιστρέφει None.

    - Θερμοκρασία ΚΑΤΩ από τη μικρότερη γραμμή του πίνακα -> Επίπεδο 1 (ασφαλές).
    - Θερμοκρασία ΠΑΝΩ από τη μεγαλύτερη γραμμή του πίνακα -> Επίπεδο 5
      (επικίνδυνο), ό,τι κι αν δείχνει η υγρασία.
    - Ενδιάμεσες τιμές -> χρησιμοποιείται η πιο κοντινή διαθέσιμη γραμμή.
    """
    rows = list(HeatIndexRow.objects.order_by("temperature"))
    if not rows:
        return None

    min_row, max_row = rows[0], rows[-1]
    if temperature < min_row.temperature:
        level_number = 1
    elif temperature > max_row.temperature:
        level_number = 5
    else:
        closest_row = min(rows, key=lambda r: abs(r.temperature - temperature))
        level_number = closest_row.level_for_humidity(humidity)

    return RiskLevel.objects.filter(level_number=level_number).first()


def record_reading(device, temperature, humidity, timestamp=None):
    """
    Κοινός πυρήνας: αποθηκεύει μια μέτρηση, αξιολογεί το επίπεδο, ενημερώνει
    τα cached πεδία της συσκευής, και στέλνει SMS αν χρειάζεται. Καλείται και
    από το /api/ingest/ (δικό μας JSON API) και από το /api/ecowitt/ (Ecowitt
    Gateway), ώστε η λογική αξιολόγησης/ειδοποίησης να είναι ΑΚΡΙΒΩΣ ίδια και
    στις δύο περιπτώσεις. Επιστρέφει το ζευγάρι (reading, risk_level).
    """
    timestamp = timestamp or timezone.now()
    risk_level = evaluate_reading(temperature, humidity)
    signal_level = f"Επίπεδο {risk_level.level_number}" if risk_level else "Χωρίς πίνακα ορίων ακόμα"
    severity = risk_level.level_number if risk_level else 0

    reading = Reading.objects.create(
        device=device, temperature=temperature, humidity=humidity,
        signal_level=signal_level, severity=severity, matched_level=risk_level,
        created_at=timestamp,
    )

    maybe_notify(device, risk_level, reading)

    device.last_seen = timestamp
    device.last_temperature = temperature
    device.last_humidity = humidity
    device.last_signal_level = signal_level
    device.last_severity = severity
    device.save(update_fields=[
        "last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity",
    ])

    return reading, risk_level


def maybe_notify(device, risk_level, reading):
    """
    Στέλνει SMS με δύο κανόνες ασφαλείας μαζί:
      1. ΠΟΤΕ δεν καθυστερεί μια ΧΕΙΡΟΤΕΡΕΥΣΗ - αν το νέο επίπεδο είναι πιο
         επικίνδυνο από ό,τι ήταν πριν, στέλνεται αμέσως, χωρίς εξαίρεση.
      2. Πέρα από αυτό, δεν στέλνεται ΚΑΝΕΝΑ νέο SMS για αυτή τη συσκευή αν
         πέρασε λιγότερο από NOTIFICATION_COOLDOWN_MINUTES από το προηγούμενο -
         ό,τι επίπεδο κι αν ήταν εκείνο. Αυτό εμποδίζει το σενάριο όπου μια
         μέτρηση ταλαντεύεται γρήγορα ανάμεσα σε δύο επίπεδα (π.χ. ακριβώς στο
         όριο) και θα έστελνε SMS σε κάθε ταλάντωση.
    """
    if risk_level is None or not risk_level.notify:
        return

    label = f"Επίπεδο {risk_level.level_number}"
    cooldown = timezone.timedelta(minutes=settings.NOTIFICATION_COOLDOWN_MINUTES)

    is_escalation = (device.last_severity or 0) < risk_level.level_number

    last_notification = (
        NotificationLog.objects.filter(device=device).order_by("-created_at").first()
    )
    global_cooldown_active = (
        last_notification is not None
        and (timezone.now() - last_notification.created_at) < cooldown
    )

    level_changed = device.last_signal_level != label
    if not is_escalation:
        if global_cooldown_active:
            return  # πολύ πρόσφατη ειδοποίηση, και δεν χειροτέρεψε -> μην ξαναστείλεις
        if not level_changed:
            return  # ίδιο επίπεδο, δεν πέρασε ακόμα ο χρόνος για reminder

    text = (
        f"[{label}] {device.name}"
        f"{f' ({device.location})' if device.location else ''}: "
        f"{reading.temperature}°C / {reading.humidity}% υγρασία. "
        f"{risk_level.message} "
        f"{('Πρόγραμμα: ' + risk_level.work_break_schedule) if risk_level.work_break_schedule else ''}"
    ).strip()

    for recipient in device.recipients.filter(is_active=True, receive_sms=True):
        if not recipient.phone_number:
            continue
        _log_and_send(device, label, text, recipient)


def _log_and_send(device, label, text, recipient):
    try:
        send_sms(recipient.phone_number, text)
        NotificationLog.objects.create(
            device=device, signal_level=label, message=text,
            channel="sms", recipient=recipient, success=True,
        )
    except Exception as exc:  # noqa: BLE001 - log and keep going
        logger.exception("Failed to send SMS alert to %s", recipient)
        NotificationLog.objects.create(
            device=device, signal_level=label, message=text,
            channel="sms", recipient=recipient, success=False, error=str(exc)[:500],
        )


# --------------------------------------------------------------------------
# SMS (μέσω SMSGate - sms-gate.app, χρησιμοποιεί Android κινητό/SIM)
# --------------------------------------------------------------------------
def send_sms(phone_number, text):
    """
    Στέλνει SMS μέσω SMSGate (sms-gate.app) - ανοιχτού κώδικα, χρησιμοποιεί το
    δικό σου Android κινητό/SIM σαν πύλη SMS, ουσιαστικά χωρίς όριο μηνυμάτων
    (μόνο ό,τι επιτρέπει το δικό σου πακέτο SMS). Χρειάζεται τα SMS_GATEWAY_URL,
    SMS_GATEWAY_USERNAME, SMS_GATEWAY_PASSWORD στο .env (τα δίνει η ίδια η
    εφαρμογή SMSGate στο κινητό σου, στην ενότητα "Cloud Server").
    """
    if not (settings.SMS_GATEWAY_URL and settings.SMS_GATEWAY_USERNAME and settings.SMS_GATEWAY_PASSWORD):
        raise RuntimeError(
            "Τα στοιχεία SMSGate δεν έχουν ρυθμιστεί (δες .env: SMS_GATEWAY_URL, SMS_GATEWAY_USERNAME, SMS_GATEWAY_PASSWORD)"
        )

    url = settings.SMS_GATEWAY_URL.rstrip("/") + "/3rdparty/v1/messages"
    response = requests.post(
        url,
        auth=(settings.SMS_GATEWAY_USERNAME, settings.SMS_GATEWAY_PASSWORD),
        json={"textMessage": {"text": text}, "phoneNumbers": [phone_number]},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()