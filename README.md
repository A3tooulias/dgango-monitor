# Climate Monitor (Django)

Εφαρμογή Django που παρακολουθεί θερμοκρασία/υγρασία σε πραγματικό χρόνο, τις συγκρίνει
με πίνακα εργασίας/ανάπαυσης λόγω ζέστης, και στέλνει **SMS** όταν χρειάζεται διάλειμμα ή
διακοπή εργασίας. Περιλαμβάνει dashboard με γράφημα, χάρτη Κύπρου με τους μετεωρολογικούς
σταθμούς, και admin για διαχείριση συσκευών/παραληπτών.

## 1. Εγκατάσταση

```powershell
pip install -r requirements.txt
copy .env.example .env        # Windows  (Linux/Mac: cp .env.example .env)
```
Άνοιξε το `.env` και συμπλήρωσε τα στοιχεία SMS (βλ. §5). Φορτώνεται **αυτόματα** μέσω
python-dotenv - δεν χρειάζεται κανένα χειροκίνητο "export" σε καμία πλατφόρμα.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_risk_levels
python manage.py collectstatic
```

Άνοιξε:
- **http://127.0.0.1:8000/** — dashboard: συσκευές, τρέχον επίπεδο, γράφημα, χάρτης Κύπρου
- **http://127.0.0.1:8000/thresholds/** — πίνακας θερμοκρασίας/υγρασίας + ρυθμίσεις επιπέδων (χρειάζεται login)
- **http://127.0.0.1:8000/admin/** — Devices + Recipients (+ Users/Groups)

## 2. Τρεις τρόποι να τροφοδοτήσεις μια συσκευή με δεδομένα

Κάθε **Device** στο admin έχει πεδίο **"Data source"** — διαλέγεις **έναν** από τους
παρακάτω τρόπους ανά συσκευή, ποτέ δύο μαζί (το admin κρύβει αυτόματα τα άσχετα πεδία):

### α) "Sensor" — δικό σου JSON API (π.χ. DIY ESP32)
```
POST /api/ingest/
Header: X-API-Key: <το api_key της συσκευής, φαίνεται στο admin>
Body:   {"temperature": 32.4, "humidity": 61.2}
```

### β) "Sensor" — Ecowitt Gateway (WN32/WH32/WH31 + GW1100/GW2000)
Ρύθμισε το Gateway σου (WS View Plus app → Weather Services → Customized) να στέλνει στο
`/api/ecowitt/` αυτού του server, πρωτόκολλο "Ecowitt". Στο admin, συμπλήρωσε
**"Ecowitt passkey"** (και "Ecowitt channel" αν είναι κανάλι πολυκάναλου WH31).

### γ) "AgroMet" — αυτόματα, από τον πλησιέστερο επίσημο μετεωρολογικό σταθμό
Καμία ανάγκη φυσικού αισθητήρα. Στο admin, γράψε στο **"Worksite address"** τη διεύθυνση
του εργοταξίου (θα σου δείξει προτάσεις ενώ γράφεις) — οι συντεταγμένες και ο πλησιέστερος
από τους ~53 σταθμούς του Τμήματος Μετεωρολογίας Κύπρου υπολογίζονται αυτόματα στο Save.

⚠️ Πηγή: [agromet.dom.org.cy](https://agromet.dom.org.cy/) / [data.gov.cy](https://data.gov.cy/en/resource/914)
— **ακατέργαστα δεδομένα** (χωρίς επίσημο quality control), ενημερωμένα κάθε ~10 λεπτά.

Το πρόγραμμα ρωτάει μόνο του τον σταθμό, περιοδικά, **χωρίς να χρειάζεται να κάνεις τίποτα**
— βλ. §4 (`poll_agromet --loop`, ξεκινάει αυτόματα μέσω `start_server.bat`). Το διάστημα
(π.χ. 5 ή 10 λεπτά) το αλλάζεις από το ίδιο dropdown "Ανανέωση κάθε" στο dashboard.

### Επιπλέον: χειροκίνητο CSV import (εφεδρικό, για κλειστές συσκευές τύπου Lascar/EasyLog)
Στο admin, δίπλα σε κάθε συσκευή, κουμπί **«📁 Upload CSV»** — ο parser αναγνωρίζει μόνος
του τις στήλες θερμοκρασίας/υγρασίας/ώρας. Δεν είναι πραγματικού χρόνου, μόνο εφεδρικό.

## 3. Το dashboard (`/`)

- **Καρτέλες συσκευών**: δυναμικές (JS), εμφανίζονται χωρίς F5 μόλις προστεθεί νέα συσκευή.
- **Πλακέτα επιπέδου**: χρώμα/κείμενο ανάλογα το επίπεδο κινδύνου (1-5) της επιλεγμένης συσκευής.
- **Γράφημα**: επιλογή εύρους (2 ώρες/6 ώρες/24 ώρες/7 μέρες), κουμπί **Export CSV** (κατεβάζει
  ό,τι βλέπεις εκείνη τη στιγμή), κουμπί **🔄 Ανανέωση τώρα** (άμεσος έλεγχος, χωρίς αναμονή).
- **Dropdown "Ανανέωση κάθε"**: ελέγχει και το πόσο συχνά ανανεώνεται η *οθόνη σου*, ΚΑΙ το
  πόσο συχνά τρέχει το AgroMet poll στο παρασκήνιο (μέσω `SystemSettings`, ζωντανά, χωρίς restart).
- **Χάρτης Κύπρου** (Leaflet + OpenStreetMap, σκουρόχρωμος): μπλε κουκκίδες = σταθμοί AgroMet,
  μεγαλύτερες χρωματιστές = οι συσκευές σου. Κουμπιά ⟲ (επαναφορά προβολής) και ⛶ (πλήρης
  οθόνη). Δύο dropdown από κάτω: πήγαινε κατευθείαν σε συγκεκριμένο εργοτάξιο ή σταθμό.

## 4. Πώς τρέχει ο server (μόνιμα, μέσω PC + Cloudflare Tunnel)

**Ένα κλικ, τρία παράθυρα μαζί:**
```powershell
.\start_server.bat
```
Ανοίγει αυτόματα:
1. **Server** — `python -m waitress --host=0.0.0.0 --port=8000 config.wsgi:application`
   (πραγματικός production server· το `runserver` δεν επαρκεί για συνεχή χρήση)
2. **Tunnel** — Cloudflare Quick Tunnel, δίνει δημόσια διεύθυνση `https://...trycloudflare.com`
   χωρίς port forwarding, χωρίς έκθεση του IP του σπιτιού/γραφείου σου. **Προσωρινή** — αλλάζει
   διεύθυνση κάθε φορά που ξανανοίγει. Για μόνιμη σταθερή διεύθυνση χρειάζεται φτηνό domain
   (~€10/χρόνο) συνδεδεμένο με Cloudflare — προαιρετική αναβάθμιση, όχι απαραίτητη τώρα.
3. **AgroMet poll** — `python manage.py poll_agromet --loop`, ρωτάει το AgroMet περιοδικά.

Αν κάτι δεν φορτώνει, πρώτος έλεγχος πάντα: `python manage.py collectstatic` μετά από
οποιαδήποτε αλλαγή CSS/JS, και restart του σωστού παραθύρου μετά από αλλαγή κώδικα.

## 5. Ειδοποιήσεις SMS (SMSGate — δωρεάν, ουσιαστικά χωρίς όριο μηνυμάτων)

1. Εγκατέστησε [SMSGate](https://sms-gate.app/) στο Android κινητό σου, ενεργοποίησε
   **"Cloud Server"**, πάτα **"Online"** — σου δίνει Username/Password.
2. Στο `.env`:
   ```
   SMS_GATEWAY_URL=https://api.sms-gate.app
   SMS_GATEWAY_USERNAME=...
   SMS_GATEWAY_PASSWORD=...
   ```
3. Στο `/admin/monitor/recipient/`, πρόσθεσε παραλήπτη (όνομα, αριθμός σε διεθνή μορφή
   +357..., τικ "Receive sms"), και σύνδεσέ τον με τις **συσκευές** που θες να παρακολουθεί
   (πεδίο "Devices" — χωρίς αυτό, ΔΕΝ λαμβάνει τίποτα, ρητή σύνδεση απαραίτητη).
4. Δοκιμή χωρίς αναμονή θερμοκρασίας: κουμπί **«📩 Send test SMS»** δίπλα σε κάθε παραλήπτη.

**Προστασία από spam**: ποτέ δεν καθυστερεί μια χειροτέρευση επιπέδου (στέλνεται αμέσως),
αλλά ανάμεσα σε δύο *οποιεσδήποτε* ειδοποιήσεις της ίδιας συσκευής περνάει τουλάχιστον
`NOTIFICATION_COOLDOWN_MINUTES` (προεπιλογή 15) — εμποδίζει σενάριο ταλάντωσης κοντά σε όριο.

## 6. Ο πίνακας θερμοκρασίας/υγρασίας (`/thresholds/`)

Κουμπί **«📋 Φόρτωση πίνακα Μέτρια εργασία (32-45°C)»** γεμίζει τον πίνακα με τα νούμερα
του φύλλου αναφοράς σου (μετά μπορείς να προσαρμόσεις οποιαδήποτε γραμμή). Στο κάτω μέρος,
5 κάρτες (Επίπεδο 1-5) όπου ορίζεις πρόγραμμα διαλείμματος, μήνυμα SMS, και αν στέλνεται
ειδοποίηση. Χρειάζεται login (οποιοσδήποτε λογαριασμός `is_staff`) — δεν είναι δημόσιο πια.

## 7. Logs και μακροπρόθεσμη διαχείριση δεδομένων

- **`logs/app.log`** — καταγραφή τεχνικών γεγονότων (π.χ. άγνωστο Ecowitt PASSKEY,
  αποτυχίες SMS/AgroMet). Γυρίζει αυτόματα στα 5MB, κρατάει τα τελευταία 5 αρχεία.
- **Δεν γεμίζει/κρασάρει η βάση με τον καιρό** — ακόμα και με πολλές συσκευές για χρόνια,
  μιλάμε για μερικά εκατοντάδες MB, εντός δυνατοτήτων SQLite.
- Προαιρετικός καθαρισμός παλιών μετρήσεων:
  ```powershell
  python manage.py cleanup_old_readings --days 365 --dry-run   # δες τι ΘΑ διαγραφόταν
  python manage.py cleanup_old_readings --days 365             # πραγματική διαγραφή
  ```

## 8. Δοκιμή χωρίς πραγματικό hardware

```powershell
python manage.py simulate_device --interval 10                          # γενικό JSON API
python manage.py simulate_device --name "X" --ramp-to-danger             # μέχρι επίπεδο 5, δοκιμή SMS
python manage.py simulate_ecowitt_device <device_id> --interval 5        # προσομοίωση Ecowitt Gateway
python manage.py simulate_ecowitt_device <device_id> --ramp-to-danger    # μέχρι επίπεδο 5
python manage.py seed_demo_readings <device_id> --hours 24               # άμεση γέμιση ιστορικού για το γράφημα
python manage.py poll_agromet                                            # ένας έλεγχος AgroMet, όχι βρόχος
```

## Δομή project

```
start_server.bat              διπλό-κλικ: ανοίγει server + tunnel + AgroMet poll μαζί
config/                       ρυθμίσεις Django (settings.py, wsgi.py)
monitor/
  models.py                    Device, RiskLevel, HeatIndexRow, Reading, Recipient,
                                NotificationLog, SystemSettings, StationObservation
  agromet.py                    σταθμοί Κύπρου + geocoding (Nominatim) + XML parser
  agromet_jobs.py                κοινή λογική poll, χρησιμοποιείται από το management command
  heat_table_preset.py          τα νούμερα του πίνακα "Μέτρια εργασία"
  services.py                  αξιολόγηση επιπέδου, αποστολή SMS, record_reading (κοινό ingest)
  views.py                     API ingestion (JSON/Ecowitt), CRUD πίνακα/επιπέδων, χάρτης, geocode
  admin.py                     Device (data_source toggle, CSV upload, geocoding) + Recipient
  static/monitor/               admin_theme.css (reskin admin), device_admin.js (autocomplete)
  templates/monitor/
    dashboard.html               αρχική: συσκευές, γράφημα, χάρτης Κύπρου
    thresholds.html               πίνακας θερμοκρασίας/υγρασίας + ρυθμίσεις επιπέδων
    csv_upload.html / test_sms.html
  templates/admin/base_site.html  φορτώνει το admin_theme.css σε όλο το admin
  management/commands/
    load_moderate_table.py, simulate_device.py, simulate_ecowitt_device.py,
    seed_demo_readings.py, seed_risk_levels.py, cleanup_old_readings.py,
    import_csv.py, poll_agromet.py
```

## Αντιμετώπιση προβλημάτων

**"no such table" / σφάλμα migration**: `python manage.py migrate`. Αν βλέπεις conflicting
migrations, δες αν έχεις δύο διαφορετικούς φακέλους project κατά λάθος (`Get-ChildItem
-Recurse -Filter db.sqlite3` για να τσεκάρεις πόσα αντίγραφα βάσης υπάρχουν).

**Η σελίδα «παγώνει» σε "Φόρτωση..."**: πιθανό JS σφάλμα νωρίτερα στο script (π.χ. αναφορά
σε στοιχείο που δεν υπάρχει πια στο HTML) εμποδίζει να τρέξει ο υπόλοιπος κώδικας. F12 →
Console για το ακριβές σφάλμα.

**Άσχημο/άστυλο admin ή dashboard**: πιθανό να μην φορτώνει το static CSS/JS — τρέξε
`python manage.py collectstatic` (yes) και restart τον server.

**Δεν στέλνονται SMS**: έλεγξε `SMS_GATEWAY_*` στο `.env`, ότι ο παραλήπτης έχει τη
συσκευή συνδεδεμένη στο πεδίο "Devices", και ότι το αντίστοιχο Επίπεδο στο `/thresholds/`
έχει «Αποστολή SMS» τικαρισμένο. Δοκίμασε πρώτα «📩 Send test SMS» (ανεξάρτητο από θερμοκρασία).

**AgroMet δεν ενημερώνεται**: βεβαιώσου ότι το παράθυρο "Climate Monitor - AgroMet" είναι
ακόμα ανοιχτό και τρέχει (`python manage.py poll_agromet --loop`), και ότι η συσκευή έχει
`data_source = "AgroMet"` (όχι "Sensor") στο admin.

**CSRF verification failed στο login**: αβλαβές, συνηθισμένο με το προσωρινό tunnel (η
σελίδα έμεινε ανοιχτή πολλή ώρα). Κάνε F5 στη σελίδα σύνδεσης και ξαναδοκίμασε.