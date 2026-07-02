from django.core.management.base import BaseCommand

from monitor.models import ThresholdRule

# Παράδειγμα 5 επιπέδων επικινδυνότητας. Αυτό είναι απλά ένα σημείο εκκίνησης -
# μπορείς να αλλάξεις τα όρια θερμοκρασίας/υγρασίας, να προσθέσεις ή να
# αφαιρέσεις επίπεδα, από τη σελίδα /thresholds/ ή από το Django admin.
DEFAULT_LEVELS = [
    dict(
        name="Επίπεδο 1 - Ασφαλές",
        severity=1,
        max_temperature=27,
        work_break_schedule="Συνεχής εργασία",
        message="Κανονικές συνθήκες.",
        notify=False,
    ),
    dict(
        name="Επίπεδο 2 - Ήπιος κίνδυνος",
        severity=2,
        min_temperature=27, max_temperature=31,
        work_break_schedule="15 λεπτά διάλειμμα ανά ώρα",
        message="Αυξημένη θερμοκρασία/υγρασία. Κάντε τακτικά μικρά διαλείμματα και ενυδατωθείτε.",
        notify=True,
    ),
    dict(
        name="Επίπεδο 3 - Μέτριος κίνδυνος",
        severity=3,
        min_temperature=31, max_temperature=34,
        work_break_schedule="Μισή ώρα διάλειμμα",
        message="Σημαντική καταπόνηση λόγω θερμότητας. Κάντε μισή ώρα διάλειμμα σε σκιά/δροσιά.",
        notify=True,
    ),
    dict(
        name="Επίπεδο 4 - Υψηλός κίνδυνος",
        severity=4,
        min_temperature=34, max_temperature=38,
        work_break_schedule="45 λεπτά διάλειμμα",
        message="Υψηλός κίνδυνος θερμικής καταπόνησης. Απαιτείται εκτεταμένο διάλειμμα.",
        notify=True,
    ),
    dict(
        name="Επίπεδο 5 - Απαγόρευση εργασίας",
        severity=5,
        min_temperature=38,
        work_break_schedule="Απαγόρευση εργασίας",
        message="Επικίνδυνες συνθήκες. Σταματήστε την εργασία άμεσα.",
        notify=True,
    ),
]


class Command(BaseCommand):
    help = "Δημιουργεί ένα παράδειγμα 5 επιπέδων επικινδυνότητας. Ασφαλές να τρέξει ξανά."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for level in DEFAULT_LEVELS:
            obj, was_created = ThresholdRule.objects.update_or_create(
                name=level["name"], defaults=level
            )
            created += was_created
            updated += not was_created
        self.stdout.write(self.style.SUCCESS(
            f"Έτοιμο. Δημιουργήθηκαν {created}, ενημερώθηκαν {updated} επίπεδα."
        ))
