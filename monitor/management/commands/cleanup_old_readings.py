from django.core.management.base import BaseCommand
from django.utils import timezone

from monitor.models import Reading


class Command(BaseCommand):
    help = (
        "Προαιρετικό: διαγράφει μετρήσεις (Reading) παλαιότερες από Χ μέρες, ώστε να "
        "μη μεγαλώνει επ' άπειρον η βάση. ΔΕΝ τρέχει αυτόματα πουθενά - μόνο αν το "
        "καλέσεις εσύ (π.χ. μία φορά τον χρόνο, ή προγραμματισμένα με Windows Task Scheduler)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=365,
            help="Διάγραψε μετρήσεις παλαιότερες από τόσες μέρες (προεπιλογή 365 = 1 χρόνος).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Μόνο δείξε πόσες θα διαγράφονταν, χωρίς να διαγράψεις πραγματικά τίποτα.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=options["days"])
        queryset = Reading.objects.filter(created_at__lt=cutoff)
        count = queryset.count()

        if options["dry_run"]:
            self.stdout.write(
                f"[Δοκιμή, τίποτα δεν διαγράφηκε] Θα διαγράφονταν {count} μετρήσεις "
                f"παλαιότερες από {cutoff:%Y-%m-%d}."
            )
            return

        queryset.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Διαγράφηκαν {count} μετρήσεις παλαιότερες από {cutoff:%Y-%m-%d}."
        ))