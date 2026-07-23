"""
Ενσωμάτωση με το δημόσιο Open Data feed του Τμήματος Μετεωρολογίας Κύπρου
(agromet.dom.org.cy / data.gov.cy) - δίκτυο ~53 αυτόματων μετεωρολογικών
σταθμών σε όλη την Κύπρο, ενημερωμένο κάθε ~10 λεπτά.

Πηγή: https://dom.org.cy/AWS/OpenData/CyDoM.xml
Dataset: https://data.gov.cy/en/resource/914 (Εθνική Πύλη Ανοιχτών Δεδομένων)

ΣΗΜΑΝΤΙΚΟ: "Weather Data Copyright The Cyprus Department of Meteorology.
This information is intended as a guide only..." - είναι δημόσιο dataset στην
επίσημη πύλη open data, αλλά είναι ΑΚΑΤΕΡΓΑΣΤΑ δεδομένα (raw, χωρίς επίσημο
quality control) - καλό να το ξέρεις για ένα σύστημα ασφαλείας.

Οι συντεταγμένες των σταθμών είναι "ψημένες" εδώ μέσα (σπάνια αλλάζουν) - μόνο
οι τρέχουσες μετρήσεις (observations) τραβιούνται φρέσκες σε κάθε poll.
"""
import math
import xml.etree.ElementTree as ET

import requests

AGROMET_XML_URL = "https://dom.org.cy/AWS/OpenData/CyDoM.xml"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# station_code -> (latitude, longitude)
AGROMET_STATIONS = {
    "ACHNA": (35.0255056, 33.7744306),
    "AGROS": (34.9148750, 33.0156667),
    "AKAMAS": (35.025974, 32.328942),
    "ALONOUDI": (34.9294861, 32.7012028),
    "AMARGETI": (34.826117, 32.588903),
    "ASTROMERITIS": (35.1330472, 33.0220222),
    "ATHALASSA": (35.140957, 33.396579),
    "ATHIENOU": (35.0502333, 33.5423000),
    "AVDIMOU": (34.6843722, 32.7573694),
    "CAVO_GRECO": (34.971012, 34.070785),
    "CHROMIO": (34.9429611, 32.8655306),
    "CYTASAT": (34.861263, 33.382527),
    "EPTAGONEIA": (34.8472556, 33.1433722),
    "FANEROMENI": (34.911600, 33.6300556),
    "FARMAKAS": (34.9209389, 33.1342389),
    "FRENAROS": (35.042400, 33.917615),
    "KALAVASOS": (34.8044694, 33.2634750),
    "KALOPANAYIOTIS": (35.0053389, 32.8262694),
    "KAMPOS": (35.072153, 32.774028),
    "KANNAVIOU": (34.9297861, 32.5859667),
    "KATHIKAS": (34.9140972, 32.4123139),
    "KEPNIC": (35.1523889, 33.3122806),
    "KILANI": (34.843888, 32.844472),
    "KORNOS": (34.913122, 33.402211),
    "KOURIS": (34.7229111, 32.9224361),
    "KPYRGOS": (35.1815639, 32.6870972),
    "KYPEROUNTA": (34.9491667, 32.9825000),
    "LCLK": (34.873476, 33.617338),
    "LCPH": (34.715442, 32.479072),
    "LEFKARA": (34.895842, 33.292878),
    "LEFKOSIA": (35.1643667, 33.3560722),
    "LIMASSOL": (34.645719, 33.003984),
    "LINOU": (35.067777, 32.898208),
    "LYSOS": (35.011868, 32.528019),
    "MALLIA": (34.8158556, 32.7851750),
    "MAMMARI": (35.1723580, 33.2148785),
    "MATHIATIS": (34.9611, 33.3310),
    "PANAGIA_BRIDGE": (35.0176028, 33.0823778),
    "PAPHOS": (34.7794306, 32.4385472),
    "PAREKLISIA": (34.7388351, 33.1590222),
    "PENTAKOMO": (34.707635, 33.261697),
    "PLATANIA": (34.9477833, 32.9258194),
    "POLIS": (35.041950, 32.437228),
    "POLYSTYPOS": (34.944042, 33.018864),
    "PRODROMOS": (34.949912, 32.830595),
    "PYRGOS": (35.1415413, 32.6163214),
    "SAITTAS": (34.8632083, 32.9113833),
    "TAMASOS": (35.0172889, 33.2491750),
    "TEPAK": (34.676960, 33.037545),
    "TRIPILOS": (34.9893528, 32.6817639),
    "TROODOS": (34.924542, 32.881496),
    "VISITOR": (35.144477, 33.403387),
    "XYLIATOS": (35.0140917, 33.0492028),
    "XYLOPHAGOU": (34.9778111, 33.8379889),
    "ZYGI": (34.7413250, 33.327100),
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Απόσταση σε km ανάμεσα σε δύο σημεία (γεωγραφικό πλάτος/μήκος)."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_nearest_station(latitude, longitude):
    """Επιστρέφει (station_code, απόσταση_σε_km) του πλησιέστερου σταθμού."""
    best_code, best_dist = None, float("inf")
    for code, (slat, slon) in AGROMET_STATIONS.items():
        dist = haversine_km(latitude, longitude, slat, slon)
        if dist < best_dist:
            best_code, best_dist = code, dist
    return best_code, best_dist


class GeocodeError(ValueError):
    """Δεν βρέθηκε καμία τοποθεσία για τη δοσμένη διεύθυνση."""


def geocode_address(address):
    """
    Μετατρέπει μια ελεύθερη διεύθυνση κειμένου (π.χ. "Λεωφόρος Μακαρίου 25,
    Λευκωσία") σε (latitude, longitude), χρησιμοποιώντας το δωρεάν, δημόσιο
    Nominatim (OpenStreetMap) - χωρίς API key, χωρίς εγγραφή. Ο περιορισμός
    "countrycodes=cy" βελτιώνει σημαντικά την ακρίβεια για κυπριακές διευθύνσεις.

    Το Nominatim ζητάει ρητά ένα αναγνωρίσιμο User-Agent (πολιτική χρήσης),
    και όριο ~1 αίτημα/δευτερόλεπτο - απόλυτα αρκετό εδώ αφού γεωκωδικοποιούμε
    μόνο όταν αποθηκεύεται/αλλάζει μια συσκευή, όχι σε κάθε poll.
    """
    if not address or not address.strip():
        raise GeocodeError("Δεν δόθηκε διεύθυνση.")

    response = requests.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1, "countrycodes": "cy"},
        headers={"User-Agent": "ClimateMonitor/1.0 (heat-stress worksite lookup)"},
        timeout=15,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise GeocodeError(f"Δεν βρέθηκε καμία τοποθεσία στην Κύπρο για: '{address}'")

    return float(results[0]["lat"]), float(results[0]["lon"])


def _short_label(result):
    """
    Φτιάχνει ένα σύντομο, καθαρό όνομα (π.χ. "Λεωφόρος Πανεπιστημίου 8,
    Αγλαντζιά, Λευκωσία") από τα δομημένα στοιχεία διεύθυνσης του Nominatim,
    αντί για το πλήρες display_name που έχει περιττές επαναλήψεις
    ("Κύπρος, Κύπρος - Kıbrıs" κλπ) - μόνο για εμφάνιση στη λίστα προτάσεων.
    """
    addr = result.get("address", {})
    parts = []

    road = addr.get("road")
    house_number = addr.get("house_number")
    if road:
        parts.append(f"{road} {house_number}" if house_number else road)

    locality = addr.get("suburb") or addr.get("city_district") or addr.get("neighbourhood")
    if locality:
        parts.append(locality)

    city = addr.get("city") or addr.get("town") or addr.get("village")
    if city and city != locality:
        parts.append(city)

    return ", ".join(parts) if parts else result["display_name"]


def search_addresses(query, limit=5):
    """
    Επιστρέφει έως `limit` πιθανές διευθύνσεις που ταιριάζουν στο query (π.χ.
    "Ομήρου 8" -> πολλές πόλεις που έχουν οδό "Ομήρου 8") - χρησιμοποιείται
    για autocomplete στο admin, ώστε ο χρήστης να διαλέξει τη σωστή αντί να
    μαντεύουμε ποια εννοούσε.
    """
    if not query or len(query.strip()) < 3:
        return []

    response = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": limit, "countrycodes": "cy", "addressdetails": 1},
        headers={"User-Agent": "ClimateMonitor/1.0 (heat-stress worksite lookup)"},
        timeout=15,
    )
    response.raise_for_status()
    results = response.json()
    return [
        {
            "display_name": r["display_name"],  # πλήρες - αποθηκεύεται, εγγυάται σωστή επανα-γεωκωδικοποίηση
            "short_label": _short_label(r),  # σύντομο - μόνο για εμφάνιση στη λίστα
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
        }
        for r in results
    ]


def parse_agromet_observations(xml_text):
    """
    Διαβάζει το XML feed και επιστρέφει ένα dict:
    { station_code: {"temperature": float|None, "humidity": float|None, "date_time": str} }
    Χρησιμοποιεί συγκεκριμένα "Air Temperature (1.2m)" και "Relative Humidity
    (1.2m)" (ύψος ανθρώπου) - ΟΧΙ το "Air Temperature (5cm)" (θερμοκρασία
    εδάφους, πολύ πιο ζεστή, άσχετη για καταπόνηση εργαζομένων).
    """
    root = ET.fromstring(xml_text)
    result = {}
    for obs_block in root.findall("observations"):
        station_code = obs_block.findtext("station_code")
        if not station_code:
            continue
        date_time_text = obs_block.findtext("date_time")
        temperature = None
        humidity = None
        for obs in obs_block.findall("observation"):
            name = (obs.findtext("observation_name") or "").strip()
            raw_value = obs.findtext("observation_value")
            if raw_value is None:
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            if name == "Air Temperature (1.2m)":
                temperature = value
            elif name == "Relative Humidity (1.2m)":
                humidity = value
        result[station_code] = {
            "temperature": temperature,
            "humidity": humidity,
            "date_time": date_time_text,
        }
    return result