from django.core.management.base import BaseCommand

from monitor.models import RiskLevel


class Command(BaseCommand):
    help = (
        "Δημιουργεί τα 5 σταθερά επίπεδα (level_number 1-5) αν λείπουν - χωρίς αυτά, "
        "η σελίδα /thresholds/ δεν έχει τίποτα να δείξει στην ενότητα 'Ρυθμίσεις ανά "
        "επίπεδο'. Ασφαλές να τρέξει ξανά, δεν πειράζει υπάρχοντα επίπεδα."
    )

    def handle(self, *args, **options):
        created = 0
        for n in range(1, 6):
            _, was_created = RiskLevel.objects.get_or_create(level_number=n)
            created += was_created
        if created:
            self.stdout.write(self.style.SUCCESS(f"Δημιουργήθηκαν {created} νέα επίπεδα."))
        else:
            self.stdout.write("Όλα τα 5 επίπεδα υπάρχουν ήδη, καμία αλλαγή.")