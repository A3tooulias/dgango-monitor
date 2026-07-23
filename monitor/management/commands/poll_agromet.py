import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from monitor.agromet_jobs import run_agromet_poll
from monitor.models import SystemSettings

CHECK_EVERY_SECONDS = 5


class Command(BaseCommand):
    help = (
        "Τραβάει τρέχουσες μετρήσεις από το AgroMet Κύπρου. Χωρίς --loop, τρέχει "
        "μία φορά. Με --loop, τρέχει για πάντα σε αυτό το παράθυρο - ελέγχει κάθε "
        f"{CHECK_EVERY_SECONDS} δευτερόλεπτα αν πέρασε το διάστημα (SystemSettings."
        "agromet_poll_minutes), οπότε αν αλλάξεις το διάστημα από το dashboard, "
        "αντιδράει σχεδόν ακαριαία - δεν χρειάζεται να περιμένεις ολόκληρο το παλιό διάστημα."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true",
            help="Τρέξε συνεχώς σε βρόχο (Ctrl+C για να σταματήσεις), αντί για μία φορά.",
        )

    def handle(self, *args, **options):
        if not options["loop"]:
            self._run_once()
            return

        self.stdout.write("Ξεκινάω βρόχο. Πάτα Ctrl+C για να σταματήσεις.")
        self._run_once()
        last_run = timezone.now()

        try:
            while True:
                time.sleep(CHECK_EVERY_SECONDS)
                minutes = SystemSettings.load().agromet_poll_minutes
                elapsed_seconds = (timezone.now() - last_run).total_seconds()
                if elapsed_seconds >= minutes * 60:
                    self._run_once()
                    last_run = timezone.now()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Σταμάτησε."))

    def _run_once(self):
        for level, message in run_agromet_poll():
            if level == "error":
                self.stdout.write(self.style.ERROR(message))
            elif level == "warning":
                self.stdout.write(self.style.WARNING(message))
            else:
                self.stdout.write(self.style.SUCCESS(message))