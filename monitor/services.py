"""
Business logic for the monitor app:
  1. evaluate_reading()  -> matches a temperature/humidity pair against your
                             ThresholdRule array and figures out the signal.
  2. maybe_notify()      -> decides whether an alert is due (state change or
                             cooldown expired) and fans it out to Viber + SMS.
  3. send_viber_message() / send_sms() -> thin wrappers around the two APIs.
"""
import logging

import requests
from django.conf import settings
from django.utils import timezone

from .models import NotificationLog, Recipient, ThresholdRule

logger = logging.getLogger(__name__)


def evaluate_reading(temperature, humidity):
    """
    Walk YOUR threshold levels, most dangerous (highest severity) first, and
    return the first one whose range matches this temperature/humidity pair.
    That way if two levels' ranges happen to overlap, the more dangerous one
    wins. Returns None if nothing matches (treated as safe / no action).
    """
    for rule in ThresholdRule.objects.order_by("-severity"):
        if rule.matches(temperature, humidity):
            return rule
    return None


def maybe_notify(device, rule, reading):
    """
    Decide whether to fire an alert for this reading, then send it.
    Notifies when:
      - there is no matching rule requiring notify=False -> skip, or
      - the device's signal level just changed, OR
      - the same signal level has persisted longer than NOTIFICATION_COOLDOWN_MINUTES
        since the last alert of that level (so DANGER conditions keep reminding you).
    """
    if rule is None or not rule.notify:
        return

    cooldown = timezone.timedelta(minutes=settings.NOTIFICATION_COOLDOWN_MINUTES)
    last_alert = (
        NotificationLog.objects.filter(device=device, signal_level=rule.name)
        .order_by("-created_at")
        .first()
    )
    level_changed = device.last_signal_level != rule.name
    cooldown_expired = last_alert is None or (timezone.now() - last_alert.created_at) >= cooldown

    if not (level_changed or cooldown_expired):
        return  # already notified recently about this exact situation

    text = (
        f"[{rule.name}] {device.name}"
        f"{f' ({device.location})' if device.location else ''}: "
        f"{reading.temperature}°C / {reading.humidity}% RH. "
        f"{rule.message} {('Πρόγραμμα: ' + rule.work_break_schedule) if rule.work_break_schedule else ''}"
    ).strip()

    recipients = Recipient.objects.filter(is_active=True)
    for recipient in recipients:
        if recipient.receive_viber and recipient.viber_user_id:
            _log_and_send(device, rule, text, "viber", recipient)
        if recipient.receive_sms and recipient.phone_number:
            _log_and_send(device, rule, text, "sms", recipient)


def _log_and_send(device, rule, text, channel, recipient):
    try:
        if channel == "viber":
            send_viber_message(recipient.viber_user_id, text)
        else:
            send_sms(recipient.phone_number, text)
        NotificationLog.objects.create(
            device=device, signal_level=rule.name, message=text,
            channel=channel, recipient=recipient, success=True,
        )
    except Exception as exc:  # noqa: BLE001 - we want to log and keep going
        logger.exception("Failed to send %s alert to %s", channel, recipient)
        NotificationLog.objects.create(
            device=device, signal_level=rule.name, message=text,
            channel=channel, recipient=recipient, success=False, error=str(exc)[:500],
        )


# --------------------------------------------------------------------------
# Viber
# --------------------------------------------------------------------------
VIBER_SEND_MESSAGE_URL = "https://chatapi.viber.com/pa/send_message"


def send_viber_message(viber_user_id, text):
    """
    Sends a text message through a Viber Public Account / Bot.
    Requires VIBER_BOT_AUTH_TOKEN to be set, and the recipient must have
    messaged your bot at least once (Viber only allows bots to message users
    who opted in) - that's how you capture their viber_user_id.
    """
    if not settings.VIBER_BOT_AUTH_TOKEN:
        raise RuntimeError("VIBER_BOT_AUTH_TOKEN is not configured")

    payload = {
        "receiver": viber_user_id,
        "type": "text",
        "sender": {"name": settings.VIBER_SENDER_NAME},
        "text": text,
    }
    headers = {"X-Viber-Auth-Token": settings.VIBER_BOT_AUTH_TOKEN}
    response = requests.post(VIBER_SEND_MESSAGE_URL, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 0:
        raise RuntimeError(f"Viber API error: {data}")
    return data


# --------------------------------------------------------------------------
# SMS (Twilio)
# --------------------------------------------------------------------------
def send_sms(phone_number, text):
    """Sends an SMS via Twilio. Requires TWILIO_* settings to be configured."""
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
        raise RuntimeError("Twilio credentials are not configured")

    from twilio.rest import Client

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(body=text, from_=settings.TWILIO_FROM_NUMBER, to=phone_number)
    return message.sid
