"""
Εισαγωγή μετρήσεων από CSV αρχείο (π.χ. export από EasyLog Cloud ή όποιο άλλο
πρόγραμμα δίνει σου μια στήλη ημερομηνίας/ώρας, μία θερμοκρασίας, και μία
υγρασίας). Ο parser αναγνωρίζει τις στήλες αυτόματα ψάχνοντας για λέξεις-
κλειδιά στις επικεφαλίδες, αντί να απαιτεί ακριβή ονόματα - έτσι δεν χρειάζεται
να ξέρουμε εκ των προτέρων την ακριβή μορφή του export.

ΣΗΜΑΝΤΙΚΟ: αυτό είναι χειροκίνητο/batch import, ΟΧΙ πραγματικός χρόνος. Κάθε
φορά που θες νέα δεδομένα, πρέπει να κάνεις export από το EasyLog Cloud και να
ανεβάσεις ξανά το αρχείο (εδώ ή με το management command import_csv).
"""
import csv
import datetime as dt
import io

from django.utils import timezone

TEMP_KEYWORDS = ["temp", "θερμοκρ", "°c", "celsius", "ch1"]
HUMIDITY_KEYWORDS = ["humid", "rh", "υγρασ", "%rh", "ch2"]
TIME_KEYWORDS = ["date", "time", "ημερομην", "ώρα", "timestamp"]

TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
]


class CsvImportError(ValueError):
    """Raised when the CSV structure can't be understood."""


def _find_column(fieldnames, keywords):
    for field in fieldnames:
        lower = field.strip().lower()
        if any(kw in lower for kw in keywords):
            return field
    return None


def _parse_timestamp(raw):
    raw = raw.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            return parsed
        except ValueError:
            continue
    return None


def parse_csv(file_obj):
    """
    Διαβάζει ένα CSV (file-like object, binary ή text) και επιστρέφει μια
    λίστα από (timestamp, temperature, humidity) tuples, ταξινομημένη
    χρονολογικά. Πετάει CsvImportError αν δεν μπορεί να βρει τις απαραίτητες
    στήλες.
    """
    raw = file_obj.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig", errors="replace")

    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        raise CsvImportError("Το αρχείο δεν έχει επικεφαλίδες στηλών (πρώτη γραμμή).")

    temp_col = _find_column(reader.fieldnames, TEMP_KEYWORDS)
    hum_col = _find_column(reader.fieldnames, HUMIDITY_KEYWORDS)
    time_col = _find_column(reader.fieldnames, TIME_KEYWORDS)

    if not temp_col or not hum_col:
        raise CsvImportError(
            "Δεν βρέθηκαν στήλες θερμοκρασίας/υγρασίας. "
            f"Στήλες που βρέθηκαν στο αρχείο: {', '.join(reader.fieldnames)}"
        )

    rows = []
    skipped = 0
    for row in reader:
        temp_raw = (row.get(temp_col) or "").strip()
        hum_raw = (row.get(hum_col) or "").strip()
        if not temp_raw or not hum_raw:
            skipped += 1
            continue
        try:
            temperature = float(temp_raw.replace(",", "."))
            humidity = float(hum_raw.replace(",", "."))
        except ValueError:
            skipped += 1
            continue

        timestamp = None
        if time_col:
            timestamp = _parse_timestamp(row.get(time_col) or "")
        if timestamp is None:
            timestamp = timezone.now()

        rows.append((timestamp, temperature, humidity))

    if not rows:
        raise CsvImportError("Δεν βρέθηκε καμία έγκυρη γραμμή δεδομένων στο αρχείο.")

    rows.sort(key=lambda r: r[0])
    return rows, skipped


def import_rows_for_device(device, rows):
    """
    Αποθηκεύει μια λίστα (timestamp, temperature, humidity) tuples σαν
    Reading για τη συγκεκριμένη συσκευή, αξιολογώντας κάθε μία έναντι του
    πίνακα ορίων. Στέλνει SMS ΜΟΝΟ για την πιο πρόσφατη μέτρηση του batch
    (όχι για κάθε ιστορική γραμμή), ώστε να μη σε πλημμυρίσει με μηνύματα.
    Επιστρέφει το πλήθος των μετρήσεων που αποθηκεύτηκαν.
    """
    from .models import Reading
    from .services import evaluate_reading, maybe_notify

    objects = []
    last_row = None
    last_level = None

    for timestamp, temperature, humidity in rows:
        risk_level = evaluate_reading(temperature, humidity)
        signal_level = f"Επίπεδο {risk_level.level_number}" if risk_level else "Χωρίς πίνακα ορίων ακόμα"
        severity = risk_level.level_number if risk_level else 0

        reading = Reading(
            device=device, temperature=temperature, humidity=humidity,
            signal_level=signal_level, severity=severity, matched_level=risk_level,
            created_at=timestamp,
        )
        objects.append(reading)
        last_row = reading
        last_level = risk_level

    Reading.objects.bulk_create(objects, batch_size=500)

    if last_row is not None:
        device.last_seen = last_row.created_at
        device.last_temperature = last_row.temperature
        device.last_humidity = last_row.humidity
        device.last_signal_level = last_row.signal_level
        device.last_severity = last_row.severity
        device.save(update_fields=[
            "last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity",
        ])
        maybe_notify(device, last_level, last_row)

    return len(objects)
