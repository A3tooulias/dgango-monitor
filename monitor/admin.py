from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html

from .csv_import import CsvImportError, import_rows_for_device, parse_csv
from .models import Device, NotificationLog, Recipient
from .services import send_sms

# Αφαιρούμε προσωρινά τα Users/Groups από το admin index (θα τα ξαναβάλουμε
# αν/όταν χρειαστεί πολλαπλούς λογαριασμούς διαχειριστών).
admin.site.unregister(User)
admin.site.unregister(Group)

# Σκόπιμα ΔΕΝ καταχωρούνται εδώ τα RiskLevel, HeatIndexRow, Reading (και το
# NotificationLog δεν έχει δικό του top-level admin):
# - Τα επίπεδα/όρια διαχειρίζονται από τη σελίδα /thresholds/ (πιο εύκολο μορφή πίνακα).
# - Το ιστορικό μετρήσεων φαίνεται σαν γράφημα στην αρχική σελίδα /.
# - Το ιστορικό ειδοποιήσεων φαίνεται μέσα στη σελίδα της κάθε συσκευής (βλ. παρακάτω).
# Το admin μένει καθαρό με μόνο τα δύο πράγματα που χρειάζονται συχνά: συσκευές και παραλήπτες SMS.


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("monitor/admin_extra.css",)}

    list_display = ["name", "location", "is_active", "is_online", "last_seen", "last_temperature", "last_humidity", "last_signal_level", "csv_upload_link"]
    readonly_fields = [
        "api_key", "usage_hint",
        "last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity",
        "recent_notifications",
    ]
    fieldsets = (
        ("Στοιχεία συσκευής", {
            "fields": ("name", "location", "is_active"),
            "description": "Συμπλήρωσε μόνο το 'Name' (υποχρεωτικό). Η τοποθεσία και το 'Is active' είναι προαιρετικά.",
        }),
        ("Πώς να τη συνδέσεις (δικό μας JSON API)", {
            "fields": ("api_key", "usage_hint"),
            "description": (
                "Το api_key δημιουργείται αυτόματα μόλις αποθηκεύσεις τη συσκευή για πρώτη φορά. "
                "Χρησιμοποίησέ το είτε για ζωντανά δεδομένα (API POST, π.χ. DIY ESP32), είτε ανέβασε CSV export παρακάτω."
            ),
        }),
        ("Ή σύνδεση μέσω Ecowitt Gateway", {
            "fields": ("ecowitt_passkey", "ecowitt_channel"),
            "description": (
                "Αν η συσκευή είναι Ecowitt (WN32/WH32/WH31 + Gateway GW1100/GW2000), συμπλήρωσε "
                "εδώ ΑΝΤΙ για api_key. Ρύθμισε το Gateway σου (WS View Plus app -> Weather Services -> "
                "Customized) να στέλνει στο <code>/api/ecowitt/</code> αυτού του server, με τύπο "
                "πρωτοκόλλου 'Ecowitt'. Άφησε το 'Channel' κενό για τον κύριο αισθητήρα (WN32/WH32), "
                "ή βάλε 1-8 αν είναι κανάλι πολυκάναλου WH31."
            ),
        }),
        ("Τρέχουσα κατάσταση (μόνο για ανάγνωση)", {
            "fields": ("last_seen", "last_temperature", "last_humidity", "last_signal_level", "last_severity"),
        }),
        ("Ιστορικό ειδοποιήσεων SMS (τελευταίες 10, μόνο για ανάγνωση)", {
            "fields": ("recent_notifications",),
            "description": "Εδώ βλέπεις αν όντως στάλθηκαν SMS για αυτή τη συσκευή, και τυχόν σφάλματα αποστολής.",
        }),
    )

    @admin.display(description="Παράδειγμα αποστολής δεδομένων")
    def usage_hint(self, obj):
        if not obj.pk:
            return "Θα εμφανιστεί εδώ ένα παράδειγμα εντολής μόλις αποθηκεύσεις τη συσκευή."
        return format_html(
            "<code>curl -X POST http://ΤΟΝ-SERVER-ΣΟΥ:8000/api/ingest/ "
            "-H \"X-API-Key: {}\" -H \"Content-Type: application/json\" "
            "-d '{{\"temperature\": 32.4, \"humidity\": 61.2}}'</code>",
            obj.api_key,
        )

    @admin.display(description="Εισαγωγή δεδομένων")
    def csv_upload_link(self, obj):
        url = reverse("admin:monitor_device_upload_csv", args=[obj.pk])
        return format_html('<a href="{}">📁 Upload CSV</a>', url)

    @admin.display(description="Πρόσφατες ειδοποιήσεις")
    def recent_notifications(self, obj):
        if not obj.pk:
            return "Θα εμφανιστεί εδώ μόλις υπάρξουν μετρήσεις που ενεργοποιούν ειδοποίηση."
        logs = NotificationLog.objects.filter(device=obj).order_by("-created_at")[:10]
        if not logs:
            return "Καμία ειδοποίηση ακόμα για αυτή τη συσκευή."
        rows = "".join(
            format_html(
                "<tr><td style='padding:4px 10px 4px 0;'>{}</td>"
                "<td style='padding:4px 10px;'>{}</td>"
                "<td style='padding:4px 10px;'>{}</td>"
                "<td style='padding:4px 0; color:{};'>{}</td></tr>",
                log.created_at.strftime("%Y-%m-%d %H:%M"),
                log.signal_level,
                log.recipient or "—",
                "green" if log.success else "crimson",
                "✓ Στάλθηκε" if log.success else f"✗ {log.error or 'Σφάλμα'}",
            )
            for log in logs
        )
        return format_html("<table>{}</table>", rows)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:device_id>/upload-csv/",
                self.admin_site.admin_view(self.upload_csv_view),
                name="monitor_device_upload_csv",
            ),
        ]
        return custom + urls

    def upload_csv_view(self, request, device_id):
        device = Device.objects.get(pk=device_id)
        result = None
        error = None

        if request.method == "POST" and request.FILES.get("csv_file"):
            try:
                rows, skipped = parse_csv(request.FILES["csv_file"])
                count = import_rows_for_device(device, rows)
                result = {"count": count, "skipped": skipped}
            except CsvImportError as exc:
                error = str(exc)
            except Exception as exc:  # noqa: BLE001
                error = f"Απρόσμενο σφάλμα: {exc}"

        return render(request, "monitor/csv_upload.html", {
            "device": device,
            "result": result,
            "error": error,
            "opts": self.model._meta,
        })


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("monitor/admin_extra.css",)}

    list_display = ["name", "phone_number", "device_list", "receive_sms", "is_active", "test_sms_link"]
    filter_horizontal = ["devices"]
    fieldsets = (
        (None, {
            "fields": ("name", "phone_number", "receive_sms", "is_active"),
            "description": (
                "Πρόσθεσε εδώ όποιον πρέπει να λαμβάνει SMS. Ο αριθμός τηλεφώνου πρέπει να είναι "
                "σε διεθνή μορφή, π.χ. +35799123456 (χωρίς κενά, με το + και τον κωδικό χώρας)."
            ),
        }),
        ("Για ποιες συσκευές ειδοποιείται", {
            "fields": ("devices",),
            "description": (
                "ΣΗΜΑΝΤΙΚΟ: χωρίς καμία επιλεγμένη συσκευή εδώ, αυτό το άτομο ΔΕΝ θα λάβει κανένα SMS. "
                "Μπορείς να συνδέσεις μία συσκευή με πολλούς παραλήπτες, ή έναν παραλήπτη με πολλές συσκευές."
            ),
        }),
    )

    @admin.display(description="Συσκευές")
    def device_list(self, obj):
        names = list(obj.devices.values_list("name", flat=True))
        return ", ".join(names) if names else "— καμία —"

    @admin.display(description="Δοκιμή")
    def test_sms_link(self, obj):
        url = reverse("admin:monitor_recipient_test_sms", args=[obj.pk])
        return format_html('<a href="{}">📩 Send test SMS</a>', url)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:recipient_id>/test-sms/",
                self.admin_site.admin_view(self.test_sms_view),
                name="monitor_recipient_test_sms",
            ),
        ]
        return custom + urls

    def test_sms_view(self, request, recipient_id):
        recipient = Recipient.objects.get(pk=recipient_id)
        result = None
        error = None

        if request.method == "POST":
            if not recipient.phone_number:
                error = "Αυτός ο παραλήπτης δεν έχει αριθμό τηλεφώνου."
            else:
                try:
                    send_sms(
                        recipient.phone_number,
                        "Δοκιμαστικό μήνυμα από το Climate Monitor. Αν το έλαβες, η αποστολή SMS λειτουργεί σωστά.",
                    )
                    result = True
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)

        return render(request, "monitor/test_sms.html", {
            "recipient": recipient,
            "result": result,
            "error": error,
            "opts": self.model._meta,
        })
