import secrets

from django.db import models
from django.utils import timezone


def generate_api_key():
    return secrets.token_hex(20)


class Device(models.Model):
    """
    Μια φυσική συσκευή/αισθητήρας WiFi θερμοκρασίας-υγρασίας.
    Κάθε συσκευή παίρνει αυτόματα ένα μοναδικό 'api_key' - αυτό είναι το
    "κλειδί" που θα βάλεις στη ρύθμιση της συσκευής/αισθητήρα ώστε να μπορεί
    να στέλνει δεδομένα σε αυτόν τον server (header X-API-Key).
    """

    name = models.CharField(
        max_length=100,
        help_text='Πώς θα φαίνεται η συσκευή στο dashboard. π.χ. "Αποθήκη Α" ή "Εργοτάξιο Βόρεια πύλη".',
    )
    location = models.CharField(
        max_length=150, blank=True,
        help_text="Προαιρετικό: πού βρίσκεται φυσικά η συσκευή (εμφανίζεται δίπλα στο όνομα).",
    )
    api_key = models.CharField(max_length=64, unique=True, default=generate_api_key, editable=False)
    is_active = models.BooleanField(
        default=True,
        help_text="Ξετίκαρε για να σταματήσεις προσωρινά να εμφανίζεται/δέχεται δεδομένα, χωρίς να τη διαγράψεις.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Προαιρετικά πεδία ΜΟΝΟ για συσκευές Ecowitt (Gateway GW1100/GW2000 + WN32/WH31).
    # Άφησέ τα κενά αν η συσκευή στέλνει δεδομένα μέσω του δικού μας JSON API (api_key).
    ecowitt_passkey = models.CharField(
        max_length=64, blank=True,
        help_text=(
            "ΜΟΝΟ για Ecowitt Gateway: το PASSKEY της συσκευής (το βρίσκεις στην εφαρμογή "
            "WS View Plus, στα στοιχεία του Gateway). Ταυτοποιεί από ποιο Gateway ήρθε η μέτρηση."
        ),
    )
    ecowitt_channel = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=(
            "ΜΟΝΟ για πολυκάναλο αισθητήρα WH31 (1-8): ποιο κανάλι αντιστοιχεί σε αυτή τη "
            "συσκευή. Άφησέ το κενό για τον κύριο/μοναδικό αισθητήρα (WN32/WH32)."
        ),
    )

    # cached fields updated on every reading, so the dashboard doesn't have
    # to hit the Reading table just to show "current status"
    last_seen = models.DateTimeField(null=True, blank=True)
    last_temperature = models.FloatField(null=True, blank=True)
    last_humidity = models.FloatField(null=True, blank=True)
    last_signal_level = models.CharField(max_length=100, blank=True)
    last_severity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.location})" if self.location else self.name

    @property
    def is_online(self):
        from django.conf import settings

        if not self.last_seen:
            return False
        cutoff = timezone.now() - timezone.timedelta(minutes=settings.DEVICE_OFFLINE_AFTER_MINUTES)
        return self.last_seen >= cutoff


class RiskLevel(models.Model):
    """
    Οι 5 σταθερές βαθμίδες επικινδυνότητας (1 = ασφαλές/συνεχής εργασία ...
    5 = απαγόρευση εργασίας). Δεν έχουν όνομα ή σειρά να ρυθμίσεις - μόνο
    πρόγραμμα διαλείμματος, μήνυμα SMS, και αν στέλνουν ειδοποίηση. ΠΟΤΕ
    ενεργοποιείται κάθε επίπεδο το αποφασίζει ο πίνακας HeatIndexRow παρακάτω.
    """

    level_number = models.PositiveSmallIntegerField(unique=True)
    work_break_schedule = models.CharField(
        max_length=100, blank=True,
        help_text='Πρόγραμμα διαλείμματος σε απλά λόγια, π.χ. "15 λεπτά διάλειμμα ανά ώρα".',
    )
    message = models.CharField(
        max_length=255, blank=True,
        help_text="Το κείμενο του SMS που θα σταλεί όταν μια συσκευή φτάσει σε αυτό το επίπεδο.",
    )
    notify = models.BooleanField(
        default=True,
        help_text="Τικ = στείλε SMS σε αυτό το επίπεδο. Ξετίκαρε για σιωπηλή καταγραφή μόνο.",
    )

    class Meta:
        ordering = ["level_number"]

    def __str__(self):
        return f"Επίπεδο {self.level_number}"


class HeatIndexRow(models.Model):
    """
    ΜΙΑ γραμμή του πίνακα εργασίας/ανάπαυσης (Μέτρια εργασία), ακριβώς όπως
    στο φύλλο αναφοράς: για μια δεδομένη θερμοκρασία, μέχρι ποιο ποσοστό
    υγρασίας ισχύει κάθε επίπεδο 1-4. Ό,τι είναι πάνω από το
    max_humidity_level4 πέφτει αυτόματα στο Επίπεδο 5.
    """

    temperature = models.IntegerField(unique=True, help_text="Θερμοκρασία σε ακέραιους βαθμούς Κελσίου (°C).")
    max_humidity_level1 = models.FloatField(help_text="Μέγιστη υγρασία (%) για Επίπεδο 1 (συνεχής εργασία).")
    max_humidity_level2 = models.FloatField(help_text="Μέγιστη υγρασία (%) για Επίπεδο 2.")
    max_humidity_level3 = models.FloatField(help_text="Μέγιστη υγρασία (%) για Επίπεδο 3.")
    max_humidity_level4 = models.FloatField(help_text="Μέγιστη υγρασία (%) για Επίπεδο 4. Πάνω από αυτό = Επίπεδο 5.")

    class Meta:
        ordering = ["temperature"]

    def __str__(self):
        return f"{self.temperature}°C"

    def level_for_humidity(self, humidity):
        if humidity <= self.max_humidity_level1:
            return 1
        if humidity <= self.max_humidity_level2:
            return 2
        if humidity <= self.max_humidity_level3:
            return 3
        if humidity <= self.max_humidity_level4:
            return 4
        return 5


class Reading(models.Model):
    """A single temperature/humidity data point coming in from a device."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="readings")
    temperature = models.FloatField(help_text="Degrees Celsius")
    humidity = models.FloatField(help_text="Relative humidity %")
    signal_level = models.CharField(max_length=100, blank=True)
    severity = models.IntegerField(null=True, blank=True)
    matched_level = models.ForeignKey(RiskLevel, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["device", "created_at"])]

    def __str__(self):
        return f"{self.device.name}: {self.temperature}°C / {self.humidity}% @ {self.created_at:%Y-%m-%d %H:%M}"


class Recipient(models.Model):
    """
    Κάποιος που πρέπει να λαμβάνει ειδοποιήσεις SMS όταν ενεργοποιείται ένα
    επίπεδο κινδύνου με notify=Ναι, ΓΙΑ ΤΙΣ ΣΥΣΚΕΥΕΣ που έχεις συνδέσει μαζί
    του. Ένας παραλήπτης χωρίς καμία συνδεδεμένη συσκευή δεν λαμβάνει τίποτα -
    η σύνδεση είναι πάντα ρητή (πεδίο "devices").
    """

    name = models.CharField(max_length=100, help_text='Όνομα για αναγνώριση, π.χ. "Γιώργος - Επόπτης".')
    phone_number = models.CharField(
        max_length=32, blank=True,
        help_text="Αριθμός κινητού σε διεθνή μορφή (E.164), π.χ. +35799123456. Εδώ θα σταλεί το SMS.",
    )
    devices = models.ManyToManyField(
        Device, related_name="recipients", blank=True,
        help_text="Για ποιες συσκευές θα ειδοποιείται. Χωρίς καμία επιλογή = καμία ειδοποίηση.",
    )
    receive_sms = models.BooleanField(default=True, help_text="Τικ = να λαμβάνει SMS ειδοποιήσεις.")
    is_active = models.BooleanField(default=True, help_text="Ξετίκαρε για προσωρινή παύση χωρίς διαγραφή.")

    def __str__(self):
        return self.name


class NotificationLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="notifications")
    signal_level = models.CharField(max_length=100)
    message = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, default="sms")
    recipient = models.ForeignKey(Recipient, on_delete=models.SET_NULL, null=True)
    success = models.BooleanField(default=False)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.device.name} -> {self.channel}:{self.recipient} [{self.signal_level}]"
