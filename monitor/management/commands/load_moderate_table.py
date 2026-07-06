from django.core.management.base import BaseCommand

from monitor.heat_table_preset import MODERATE_WORK_TABLE
from monitor.models import HeatIndexRow


class Command(BaseCommand):
    help = 'Φορτώνει τον πίνακα "Μέτρια εργασία" (32-45°C) - το ίδιο που κάνει το κουμπί στη σελίδα /thresholds/.'

    def handle(self, *args, **options):
        HeatIndexRow.objects.all().delete()
        HeatIndexRow.objects.bulk_create([
            HeatIndexRow(
                temperature=row[0], max_humidity_level1=row[1],
                max_humidity_level2=row[2], max_humidity_level3=row[3], max_humidity_level4=row[4],
            )
            for row in MODERATE_WORK_TABLE
        ])
        self.stdout.write(self.style.SUCCESS(f"Έτοιμο. Φορτώθηκαν {len(MODERATE_WORK_TABLE)} γραμμές."))
