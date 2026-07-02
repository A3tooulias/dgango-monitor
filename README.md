# Climate Monitor (Django)

Εφαρμογή Django που δέχεται σε πραγματικό χρόνο μετρήσεις θερμοκρασίας/υγρασίας από
πολλαπλές συσκευές (WiFi αισθητήρες, π.χ. τύπου Lascar EL-WiFi), τις συγκρίνει με τα
δικά σου επίπεδα επικινδυνότητας, και στέλνει ειδοποίηση Viber ή SMS όταν χρειάζεται
διάλειμμα ή διακοπή εργασίας. Περιλαμβάνει dashboard με γράφημα που ανανεώνεται κάθε
5-10 λεπτά.

## 1. Εγκατάσταση

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # και συμπλήρωσε τα κλειδιά σου
export $(cat .env | xargs)    # ή load το .env με python-dotenv/direnv

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_thresholds   # δημιουργεί 5 παραδειγματικά επίπεδα
python manage.py runserver
```

Άνοιξε:
- **http://127.0.0.1:8000/** — dashboard με γράφημα θερμοκρασίας/υγρασίας
- **http://127.0.0.1:8000/thresholds/** — εδώ ορίζεις ΜΟΝΟΣ ΣΟΥ τα επίπεδα επικινδυνότητας
- **http://127.0.0.1:8000/admin/** — διαχείριση συσκευών, παραληπτών ειδοποιήσεων, ιστορικού

## 2. Ορισμός επιπέδων επικινδυνότητας (χωρίς κώδικα)

Στη σελίδα `/thresholds/` μπορείς να:
- **Προσθέσεις ή αφαιρέσεις όσα επίπεδα θέλεις** (όχι μόνο 5 — βάλε όσα σε βολεύουν).
- Ορίσεις για κάθε επίπεδο: ελάχιστη/μέγιστη θερμοκρασία (°C) και υγρασία (%).
- Επιλέξεις πρόγραμμα διαλείμματος από έτοιμες επιλογές (συνεχής εργασία / 15 λεπτά
  ανά ώρα / μισή ώρα / 45 λεπτά / απαγόρευση εργασίας) ή να γράψεις το δικό σου.
- Με ένα **τικ** να αποφασίσεις αν αυτό το επίπεδο θα στέλνει ειδοποίηση Viber/SMS.
- Ορίσεις τη **σοβαρότητα** (1 = ασφαλέστερο, μεγαλύτερος αριθμός = πιο επικίνδυνο).
  Όταν μια μέτρηση ταιριάζει σε παραπάνω από ένα επίπεδο ταυτόχρονα, κερδίζει πάντα
  το πιο σοβαρό.

Οι αλλαγές ισχύουν αμέσως — δεν χρειάζεται restart του server.

## 3. Σύνδεση συσκευών (αισθητήρων)

1. Στο `/admin/monitor/device/`, πρόσθεσε μια συσκευή. Θα δημιουργηθεί αυτόματα ένα
   `api_key`.
2. Ο αισθητήρας στέλνει (HTTP POST) κάθε φορά που παίρνει μέτρηση:

```bash
curl -X POST http://YOUR_SERVER:8000/api/ingest/ \
  -H "X-API-Key: <το api_key της συσκευής>" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 32.4, "humidity": 61.2}'
```

Η απάντηση λέει αμέσως ποιο επίπεδο ενεργοποιήθηκε:

```json
{
  "stored": true,
  "signal_level": "Επίπεδο 3 - Μέτριος κίνδυνος",
  "severity": 3,
  "message": "Σημαντική καταπόνηση λόγω θερμότητας...",
  "work_break_schedule": "Μισή ώρα διάλειμμα"
}
```

Μπορείς να συνδέσεις όσες συσκευές θέλεις — καθεμία με δικό της `api_key`,
εμφανίζονται όλες σαν καρτέλες στο dashboard.

**Δεν έχεις ακόμα πραγματικό αισθητήρα;** Δοκίμασε τον προσομοιωτή:

```bash
python manage.py simulate_device --interval 10
```

Αυτό δημιουργεί μια εικονική συσκευή "Demo Sensor" και στέλνει τυχαίες μετρήσεις
κάθε 10 δευτερόλεπτα, ώστε να δεις το dashboard να ζωντανεύει.

## 4. Ειδοποιήσεις Viber / SMS

Στο `/admin/monitor/recipient/` πρόσθεσε ανθρώπους που πρέπει να ειδοποιούνται,
με το τηλέφωνό τους (για SMS) ή/και το Viber user ID τους (για Viber).

- **Viber**: χρειάζεσαι Viber Public Account/Bot (partners.viber.com) και το auth
  token του στο `.env` (`VIBER_BOT_AUTH_TOKEN`). Ο κάθε παραλήπτης πρέπει να έχει
  στείλει μήνυμα στο bot μία φορά πριν μπορεί το bot να του στείλει πίσω — έτσι
  αποκτάς το `viber_user_id` του (θα το δεις στο webhook/API log του bot σου).
- **SMS**: χρειάζεσαι λογαριασμό Twilio (ή αλλάζεις το `send_sms()` στο
  `monitor/services.py` για όποιον πάροχο SMS προτιμάς) και τα στοιχεία του στο `.env`.

Η εφαρμογή δεν στέλνει ειδοποίηση σε κάθε μέτρηση — μόνο όταν αλλάζει επίπεδο ή
όταν περάσουν `NOTIFICATION_COOLDOWN_MINUTES` (προεπιλογή 15) από την τελευταία
ειδοποίηση ίδιου επιπέδου, ώστε να μη σε πλημμυρίζει με μηνύματα.

## 5. Γράφημα σε πραγματικό χρόνο

Το dashboard (`/`) δείχνει το τρέχον επίπεδο, θερμοκρασία/υγρασία, και ένα γράφημα
των τελευταίων 2 ωρών. Ανανεώνεται αυτόματα κάθε 5 ή 10 λεπτά (επιλογή πάνω δεξιά).
Τα δεδομένα έρχονται από `GET /api/devices/<id>/readings/?minutes=120`.

## Δομή project

```
config/            ρυθμίσεις Django (settings, urls)
monitor/
  models.py         Device, ThresholdRule, Reading, Recipient, NotificationLog
  services.py       αξιολόγηση μετρήσεων + αποστολή Viber/SMS
  views.py          API ingestion, API επιπέδων (CRUD), σελίδες dashboard/thresholds
  templates/monitor/dashboard.html    πίνακας ελέγχου με γράφημα
  templates/monitor/thresholds.html   διαχείριση επιπέδων επικινδυνότητας
  management/commands/
    seed_thresholds.py    παράδειγμα 5 επιπέδων
    simulate_device.py    προσομοίωση συσκευής για δοκιμή χωρίς hardware
```

## Σημειώσεις παραγωγής (production)

- Άλλαξε `DJANGO_SECRET_KEY`, βάλε `DJANGO_DEBUG=0`, όρισε σωστά `DJANGO_ALLOWED_HOSTS`.
- Το API `/api/thresholds/` και `/api/ingest/` δεν έχουν authentication πέρα από το
  API key της συσκευής — αν η εφαρμογή θα είναι προσβάσιμη από το internet (όχι μόνο
  τοπικό δίκτυο), πρόσθεσε π.χ. Django login στη σελίδα `/thresholds/` και IP
  allowlisting ή HTTPS + reverse proxy μπροστά από τον server.
- Για πολλές συσκευές/υψηλή συχνότητα μετρήσεων σε production, βάλε PostgreSQL αντί
  για SQLite (άλλαξε `DATABASES` στο `config/settings.py`) και τρέξε πίσω από
  gunicorn/nginx.
