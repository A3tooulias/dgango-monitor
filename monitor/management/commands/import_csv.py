from django.core.management.base import BaseCommand, CommandError

from monitor.csv_import import CsvImportError, import_rows_for_device, parse_csv
from monitor.models import Device


class Command(BaseCommand):
    help = "Εισάγει μετρήσεις από ένα CSV αρχείο (π.χ. export από EasyLog Cloud) για μια συσκευή."

    def add_arguments(self, parser):
        parser.add_argument("device_id", type=int, help="Το ID της συσκευής (φαίνεται στο admin).")
        parser.add_argument("csv_path", type=str, help="Διαδρομή προς το .csv αρχείο.")

    def handle(self, *args, **options):
        try:
            device = Device.objects.get(id=options["device_id"])
        except Device.DoesNotExist:
            raise CommandError(f"Δεν βρέθηκε συσκευή με id={options['device_id']}")

        try:
            with open(options["csv_path"], "rb") as f:
                rows, skipped = parse_csv(f)
        except FileNotFoundError:
            raise CommandError(f"Δεν βρέθηκε το αρχείο: {options['csv_path']}")
        except CsvImportError as exc:
            raise CommandError(str(exc))

        count = import_rows_for_device(device, rows)
        self.stdout.write(self.style.SUCCESS(
            f"Έτοιμο. Εισήχθησαν {count} μετρήσεις για τη συσκευή '{device.name}' "
            f"({skipped} γραμμές παραλείφθηκαν λόγω κενών/μη έγκυρων τιμών)."
        ))
