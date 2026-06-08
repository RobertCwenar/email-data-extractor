# Library

import imaplib
from bs4 import BeautifulSoup
from email import message_from_bytes
import email
import pandas as pd
import os
from dotenv import load_dotenv
import re
import email.utils

# Load environment variables
load_dotenv()

# Login to wp.pl
mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
login_email = os.getenv("EMAIL").strip().replace(",", "")
my_password = os.getenv("PASSWORD").strip().replace(",", "")
print("Logging in:", bool(login_email))
print("Password loaded:", bool(my_password))

mail.login(login_email, my_password)

mail.select("PRACA") 

status, messages = mail.search(None, "ALL")

mail_ids = messages[0].split()


print("Number of emails:", len(mail_ids))


# load data

jobs = []

def get_html(msg):
    if msg is None:
        return None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        if msg.get_content_type() == "text/html":
            return msg.get_payload(decode=True).decode(errors="ignore")
    return None


def clean_block(block):
    cleaned = []

    for line in block:
        l = line.lower()

        if l in ["!", "nowość!", "nowość", "hit!", "śpiesz się!"]:
            continue

        if "z " in l and "." in l:
            continue

        cleaned.append(line)

    return cleaned


skip = skip = [
    "logo", "więcej", "ciepłe", "najlepiej dopasowana", 
    "nowość", "hit", "śpiesz się",
    "krajowego rejestru", "krs", "nip", "regon", 
    "kapitału zakładowego", "wpłacony w całości", "ul. prosta", 
    "wyprzedź innych kandydatów", "Zobacz oferty, które mogły Ci umknąć", "bądź na bieżąco z nowymi ofertami pracy", 
    "zobacz wszystkie oferty pracy", 
    "zobacz wszystkie oferty", "zobacz więcej ofert", "zobacz więcej", "zobacz inne oferty", "zobacz inne", 
    "zobacz podobne oferty", "zobacz podobne", "sprawdź inne oferty", 
    "sprawdź inne", 
    "sprawdź podobne oferty", 
    "sprawdź podobne",
]

bad_titles = [
    "najlepiej dopasowana",
    "nowość",
    "hit",
]

def looks_like_job(title):
    if not title or not isinstance(title, str):
        return False

    title = title.lower()

    keywords = [
        "analityk", 
        "analyst", 
        "specjalista",
        "developer", 
        "konsultant", 
        "księgowy",
        "staż", 
        "młodszy", 
        "data", 
        "it", 
        "danych",
        'business', 
        'controlling', 
        'finanse', 
        'finance', 
        'planowania', 
        'planowanie', 
        'kontroler',
        'kontroler finansowy',
        'raportowanie',
        'raporty',
        'raportowania', 
        "archiwum", 
        "biurowy", 
        "fakturowania", 
        "spedytor", 
        "menedżer",  
        "logist", 
        "supply"
    ]
    exclude = [
        "sp. z o.o", 
        "s.a.", 
        "sa ", 
        " sp. z", 
        "bank", 
        "polska"
    ]

    if any (k in title for k in keywords):
        if not any(e in title for e in exclude):
            return True
    return False


def is_job_trigger(line):
    keywords = [
    "analityk",
    "analyst",
    "specjalista",
    "specjalistka",
    "developer",
    "engineer",
    "konsultant",
    "staż",
    "intern",
    "kontroler",
    "finansowy",
    "it",
    "data",
    "business"
    ]

    return any(k in line.lower() for k in keywords)

def Knows_Companies(company):
    known_companies = [

    "komornik sądowy przy sądzie rejonowym dla wrocławia-fabrycznej we wrocławiu dawid węgrzyk kancelaria",
    "partner papes sp. z o.o. (ogólnopolska grupa kompania biurowa)",
    "pge energetyka kolejowa s.a - oddział usługi",
    "polski bank komórek macierzystych spółka z ograniczoną odpowiedzialnością",
    "puckator european distribution centre spółka z ograniczona odpowiedzialnością",
    "uniformix marcin błędowski spółka komandytowo-akcyjna",
    "wsparcie działu administracyjno-księgowego (k/m/i- w tym osoba niepełnosprawna)",
    "pracownik administracyjny z językiem angielskim - zmiana popołudniowa (k/m/x)",
    "konsulat generalny republiki federalnej niemiec we wrocławiu",
    "compensa towarzystwo ubezpieczeń s.a. vienna insurance group",
    "dla-wspólnoty.pl zarządzanie nieruchomościami jakub szpiegowski",
    "intelligent solutions polska sp. z o.o. sp. komandytowa",
    "wpcaravans centrum kempingowe spółka z ograniczoną odpowiedzialnością",
    "bsh sprzęt gospodarstwa domowego sp. z o.o.",
    "ceglana spółka z ograniczoną odpowiedzialnością",
    "cloudfide spółka z ograniczoną odpowiedzialnością",
    "ensera - nazwa handlowa steripack medical poland sp. z o.o.",
    "farmaceutyczna spółdzielnia pracy „galena”",
    "mahle thermal and fluid systems poland sp. z o.o.",
    "mckinsey knowledge center poland sp. z o.o.",
    "optiveum spółka z ograniczoną odpowiedzialnością",
    "paypo spółka z ograniczoną odpowiedzialnością",
    "pge energetyka kolejowa operator sp. z o.o.",
    "ppg global business services poland sp. z o.o.",
    "refunda maciocha i wspólnicy spółka komandytowa",
    "rgb elektronika spółka z ograniczoną odpowiedzialnością",
    "sagaris constructions spółka z ograniczoną odpowiedzialnością",
    "strix poland spółka z ograniczoną odpowiedzialnością",
    "upvanta spółka z ograniczoną odpowiedzialnością",
    "vaco retail spółka z ograniczoną odpowiedzialnością",
    "acxiom global service center polska sp. z o. o",
    "agat group spółka z ograniczoną odpowiedzialnością",
    "apcom development spółka z ograniczoną odpowiedzialnością",
    "automat-spec sp. z o.o. sp. k.",
    "biuro rachunkowe tributo sp. z o.o.",
    "dolnośląskie przedsiębiorstwo napraw infrastruktury komunikacyjnej dolkom sp. z o.o.",
    "dolnośląski fundusz rozwoju sp. z o.o.",
    "elim international spółka z ograniczoną odpowiedzialnością",
    "epp spółka z ograniczoną odpowiedzialnością",
    "fis technology services poland sp. z o.o.",
    "fresenius medical care emea gbs sp. z o.o.",
    "involt sp. z o.o. spółka komandytowa",
    "keim farby mineralne spółka z ograniczoną odpowiedzialnością",
    "loyalty partner polska sp. z o.o. (payback)",
    "mako tsl spółka z ograniczoną odpowiedzialnością",
    "metz display polska sp. z o.o.",
    "mx solution spółka z ograniczoną odpowiedzialnością",
    "neontri spółka z ograniczoną odpowiedzialnością",
    "nutricia zakłady produkcyjne sp. z o.o.",
    "parker hannifin manufacturing poland sp. z o.o.",
    "polska sieć handlowa livio plus sp. z o.o.",
    "rhino spółka z ograniczoną odpowiedzialnością",
    "seco cosmetics spółka z ograniczoną odpowiedzialnością",
    "sobota jachira kancelaria prawna spółka komandytowa",
    "sport supplements ltd sp z oo. oddział w polsce",
    "supervista poland sp. z o.o.",
    "technika klimatyzacyjna i grzewcza sp. z o.o.",
    "uniwersytet ekonomiczny we wrocławiu",
    "vfs usługi finansowe polska sp. z o.o.",
    "zautomatyzujmy.to sp. z o.o.",
    "eko-tech przedsiębiorstwo projektowo - usługowe sp. z o.o.",
    "mm agencja marketingu ekologicznego sp. z o.o.",
    "arcos fm pl saller polbau sp. z o.o. sp. k.",
    "balmain property management sp. z o.o.",
    "finance business partners sp. z o.o.",
    "fluidra polska spółka z ograniczoną odpowiedzialnością",
    "gates business services europe sp. z o.o.",
    "innovative facility management polska sp. z o.o.",
    "panasonic cold chain poland sp. z o.o.",
    "regionalny przedstawiciel handlowie - branża medyczna",
    "umicore battery materials poland sp. z o.o.",
    "wyższa szkoła kształcenia zawodowego",
    "agro brokers transport sp. z o.o.",
    "bank spółdzielczy w kobierzycach",
    "berlinerluft. technik sp. z o.o.",
    "chias brothers europe sp. z o.o.",
    "epam systems (poland) sp. z o.o.",
    "horizon-automation sp. z o.o. sp. k.",
    "kancelaria notarialna agnieszka marek-gąsiorowska",
    "mahle shared services poland sp. z o.o.",
    "tauron obsługa klienta sp. z o.o.",
    "atos poland global services sp. z o.o.",
    "credit agricole bank polska s.a.",
    "integer group services sp. z o.o",
    "kuehne + nagel sp. z o.o.",
    "life spot management sp. z o.o.",
    "m&b biuro rachunkowe sp. z o.o.",
    "network experts sp. z o.o. sp.k.",
    "osiedle malownicze sp. z o.o. sk",
    "raben management services sp. z o.o.",
    "tauron dystrybucja spółka akcyjna",
    "voss automotive polska sp. z o.o.",
    "zdemar polska sp. z o.o. sk",
    "acturis poland sp. z o.o.",
    "adecco poland sp. z o.o.",
    "anter system polska sp. z. o.o.",
    "atlas ward polska sp. z o.o.",
    "aurovitas pharma pharma sp. z o.o.",
    "biuro obsługi kancelarii sp. z o.o.",
    "bnp paribas bank polska s.a.",
    "browar stu mostów sp. z o.o.",
    "cityfit management sp. z o.o.",
    "deerfos europe sp. z o.o.",
    "edge one solutions sp. z o.o.",
    "electrolux poland sp. z o.o.",
    "elenger polska sp. z o.o.",
    "eurocash serwis sp. z o.o.",
    "ey (dawniej ernst & young)",
    "gispartner sp. z o.o.",
    "global24 sp. z o.o. sp. k.",
    "ideal automotive świdnica sp. z o.o.",
    "ingram micro services spółka z o.o.",
    "kb food&catering sp. z o.o.",
    "limango polska sp. z o.o.",
    "logistik sp. z o.o.",
    "mondi solec sp. z o.o.",
    "nexio management sp. z o.o.o",
    "ortie capital investment s.a.",
    "przedsiębiorstwo hak sp. z o.o.",
    "raben logistics polska sp. z o.o.",
    "romay sp. z o.o.",
    "ronal polska sp. z o.o.",
    "santander consumer bank sa",
    "schavemaker invest sp. z o.o.",
    "schavemaker poland sp. z o.o.",
    "shankarpack poland sp. z o.o.",
    "smith&nephew sp. z o.o.",
    "square one resources sp. z o.o.",
    "starion poland sp. z o.o.",
    "sybilla technologies spółka z o.o.",
    "usi asteelflash poland sp. z o.o",
    "votum consumer care sp. z o.o.",
    "vorwerk polska sp. z o.o. sp. k.",
    "wrocławskie inwestycje sp. z o.o.",
    "zakład techniki kanalizacyjnej jarosław mijalski",
    "axa xl catlin services se",
    "btl poland logistics sp. z o. o.",
    "centrala farmaceutyczna cefarm s a",
    "elko bis systemy odgromowe",
    "gkn driveline polska sp. z o.o.",
    "kaczmarski group",
    "leasingteam professional",
    "leroy merlin polska sp. z o.o.",
    "pkp informatyka spółka z o.o.",
    "plannista/-ka międzynarodowy/-a (k/m)",
    "polska grupa farmaceutyczna sp. z o.o.",
    "pomorska specjalna strefa ekonomiczna sp. z o.o.",
    "prezero service zachód sp. z o.o.",
    "rohlig suus logistics s.a.",
    "toyota tsusho europe s.a.",
    "agencja rozwoju przemysłu s.a.",
    "apleona polska sp. z o.o.",
    "asseco poland s.a.",
    "asystentka/asystent w dziale administracji",
    "axfina polska sp. z o.o.",
    "b2b.net s.a.",
    "bank millennium s.a.",
    "bank pocztowy s.a.",
    "bcf software sp. z o.o.",
    "beeline poland sp. z o.o.",
    "benefit systems s.a.",
    "bzb uas sp. z o.o.",
    "carden group sp. z o.o.",
    "chemeko-system sp. z o.o.",
    "concordia design sp. z o.o.",
    "controltec sp. z o.o.",
    "de gruyter brill sp z o.o.",
    "descont sp. z o.o. sp.k.",
    "dobry materiał sp. z o.o.",
    "e-trade automation sp. z o.o.",
    "elkrem spółka z ograniczoną odpowiedzialnością",
    "enchem poland sp. z o.o.",
    "entire m sp. z o.o.",
    "eos poland sp. z o.o.",
    "eurostat poland sp. z o.o.",
    "evesta sp. z o.o.",
    "exclusive worldwide sp. z o.o.",
    "farutex sp. z o.o.o",
    "feroporto sp. z o.o.",
    "gamefound sp. z o.o.",
    "greek trade sp. z o.o.",
    "hewea sp. z o.o.o",
    "hubergroup polska sp. z o.o.",
    "ilogic sp. z o.o.",
    "in4ge sp. z o.o.",
    "infac poland sp. z o.o.",
    "karpaty trade sp. z o.o.",
    "leader logistics sp. z o.o.",
    "lime access sp. z o.o.",
    "lizard sp. z o.o. sp. komandytowa",
    "logizen sp. z o.o.",
    "lottomerkury sp. z o.o.",
    "natek poland",
    "nobilis aurum sp. z o.o.",
    "no limit sp. z o.o.",
    "nordes sp. z o.o.",
    "nova spine sp. z o.o.",
    "novum finance sp. z o.o.",
    "oferteo spółka akcyjna",
    "oleofarm sp. z o. o.",
    "optima logistics group s.a.",
    "orlen paczka sp. z o.o.",
    "owner cfo sp. z o.o.",
    "oze plus sp. z o.o.",
    "p.p.f hasco-lek s.a.",
    "phinance s.a.",
    "pib group poland spółka z ograniczoną odpowiedzialnością",
    "popławska group spółka jawna",
    "q-group sp. z o.o.",
    "rekord si sp. z o.o.",
    "room99 sp. z o.o.",
    "satagro sp. z o.o.",
    "selena fm s.a.",
    "sii sp. z o.o.",
    "simplifae poland spółka akcyjna",
    "spline sp. z o. o.",
    "stator sp. z o.o.",
    "stock polska sp. z o.o.",
    "swift recruitment sp. z o.o.",
    "tremezzo sp. z o.o.",
    "unisoft sp. z o.o.",
    "univio sp. z o.o.",
    "urtica sp. z o.o.",
    "veloleasing s.a.",
    "verocargo sp. z o.o.",
    "vimana sp. z o.o.",
    "velobank s.a.",
    "wpo alba s.a.",
    "your iteams sp. z o.o.",
    "znanysystem sp. z o.o.",
    "7technology sp. z o.o.",
    "adsystem sp. z o.o.",
    "agrowe app sp. z o.o.",
    "alkla sp. z o.o.",
    "auto-marpo części do aut japońskich",
    "basf catalysts polska sp. z o.o.",
    "capgemini polska",
    "centum sp. z o.o.",
    "convista poland",
    "cursor s.a.",
    "cyberrescue sp. z o.o.",
    "dcg centrum medyczne",
    "dcx polska sp. z o.o.",
    "diagnostyka s.a.",
    "dijo baking sp. z o.o.",
    "donako sp. z o.o.",
    "doz s.a.",
    "edaxo sp. z o.o.",
    "efl sa",
    "ekovo sp. z o.o.",
    "elenger",
    "elemont s.a.",
    "eservice sp. z o.o.",
    "fm integrated solutions sp. z o.o.",
    "forvis mazars",
    "friendly solutions",
    "gea invest sp. z o.o.",
    "gloria funeral sp. z o.o.",
    "gojump - park trampolin",
    "goldenmark center sp. z o.o.",
    "hicron sp. z o.o.",
    "hi-m solutek poland sp. z o.o.",
    "hoist polska sp. z o.o.",
    "home&you s.a.",
    "ibss biomed s.a.",
    "id logistics polska s.a.",
    "ifs sp. z o.o.",
    "insert s.a.",
    "interson",
    "investa sp. z o.o.",
    "item polska",
    "jelcz sp. z o.o.",
    "jones lang lasalle & tétris",
    "jti polska sp. z o.o.",
    "kancelaria signi s.a.",
    "klient pracuj.pl",
    "kruk s.a.",
    "lhh recruitment solutions",
    "lg innotek poland sp. z o.o.",
    "luxiona poland s.a.",
    "lyreco advantage",
    "mondi sp. z o. o.",
    "myorlen sp. z o.o.",
    "nara battery engineering poland",
    "nask",
    "nasz prąd s.a.",
    "pgf sp. z o.o.",
    "park 1 sp. z o.o.",
    "penta hospitals polska",
    "pko bank polski sa",
    "polkomtel",
    "ppg deco polska sp. z o.o",
    "presscom sp. z o.o.",
    "procam polska sp. z o.o.",
    "prosystem s.a.",
    "provident polska",
    "ray trans sp. z o.o.",
    "roltec sp. z o.o.",
    "sii",
    "skytaxi sp. z o.o.",
    "smartlunch s.a.",
    "sollers consulting",
    "sonko sp. z o.o.",
    "speedmag sp. z o.o.",
    "spyrosoft s.a.",
    "supravis s.a.",
    "tarczyński s.a.",
    "telforceone s.a.",
    "tim s.a.",
    "tjx poland sp. z o.o.",
    "totalizator sportowy",
    "trakcja s.a.",
    "transcash.eu s.a.",
    "tuir warta s.a.",
    "unionalpha s.p.a. oddział w polsce",
    "votum",
    "weartech solutions sp. z o.o.",
    "zaberd spółka z o.o.",
    "adama manufacturing poland s.a.",
    "alab laboratoria sp z o.o.",
    "archicom s a",
    "asystent / asystentka zarządu",
    "asystent / asystentka biura",
    "audiofon",
    "autoliv poland sp. z o.o.",
    "b2 impact s.a.",
    "bergman engineering sp. z o.o.",
    "c.h. robinson",
    "collins aerospace",
    "consdata s.a.",
    "dhl global forwarding",
    "dsv gbs",
    "dsv road",
    "duvenbeck",
    "ergo hestia",
    "erste bank polska",
    "evercrane sp. z o.o.",
    "ewl group",
    "exn sp. z o.o.",
    "fbserwis s a",
    "faurecia wałbrzych sa",
    "find work",
    "greek trade",
    "green grain",
    "grupa aterima",
    "grupa eneris",
    "grupa pascal",
    "grupa pcc",
    "grupa progres",
    "grupa pzu",
    "grupa vantage",
    "gungan sp. z o.o.",
    "hays poland",
    "inpost",
    "integralia",
    "kaufland",
    "kpmg",
    "lpp s.a.",
    "manpower",
    "materialise",
    "media expert",
    "medicover",
    "medipe",
    "michael page",
    "milado centrum rozwoju personalnego sp. z o.o.",
    "moltres energy p.s.a.",
    "mymurapol sp. z o.o.",
    "nettle",
    "netia",
    "omida vls sp. z o.o.",
    "orison sp. z o.o.",
    "pasibus",
    "pewny lokal",
    "poczta polska",
    "pwc",
    "quickpack polska",
    "r partner",
    "rolladen group",
    "rtv euro agd",
    "sandwicz szop",
    "sklepcaraudio.pl",
    "streamsoft",
    "tim",
    "toya sa",
    "trenkwalder",
    "tu europa sa",
    "uhy eca",
    "univio",
    "us pharmacia",
    "usp zdrowie",
    "vidis sa",
    "votum",
    "wpo alba s.a.",
    "xeos sp. z o.o.",
    "zooplus",
    "żywiec",
    "amazon",
    "astek",
    "atm grupa s.a.",
    "bank pekao",
    "beata wróblewska",
    "codetwo",
    "dsv",
    "energia polska",
    "ey",
    "firma softex dariusz michta",
    "grupa zabezpiecz auto",
    "inpost",
    "lorenz p.s.a.",
    "lpp",
    "mateusz makowski",
    "max-fliz",
    "mondi",
    "nazwa.pl",
    "nes fircroft",
    "nest lease s.a.",
    "nestlé purina",
    "nokia",
    "nosta logistik sp. z o.o.",
    "olsztyn",
    "poczta",
    "polkomtel",
    "port lotniczy",
    "ppg",
    "pwc",
    "rafineria",
    "santander",
    "tui",
    "ups",
    "warta",
    "xeos",
    "zf",
    "żabka polska"
]
    
    company = company.lower().strip()

    company = (
        company.replace(" sp. z o.o.", "")
        .replace(" sp. z o.o", "")
        .replace(".", "")
        .replace(",", "")
        .replace("sa ", "sa")
    )

    company = re.sub(r'\s+', ' ', company)
    company = re.sub(r'\s*-\s*', ' ', company)

    return any(kc in company for kc in known_companies)

def is_valid_job(job):
    title = job["title"].lower()


    if any(b in title for b in bad_titles):
        return False

    # It should be like a job title, not just a single word
    if len(title.split()) < 2:
        return False

    # company not offering jobs
    if "sp. z o.o" in title.lower():
        return False

    return True

clean_jobs = []
status, response = mail.search(None, 'ALL')
mail_ids = response[0].split()

if not mail_ids:
        print("No new job offers found.")
else:
        print(f"Found {len(mail_ids)} new emails.")

Cache_file = "processed_mails.txt"
if os .path.exists(Cache_file):
    with open(Cache_file, "r") as f:
        processed_ids = set(line.strip() for line in f)
else:
    processed_ids = set()



# Main processing loop

for i in mail_ids:
    mail_id_str = i.decode() if isinstance(i, bytes) else str(i)

    if mail_id_str in processed_ids:
        continue
    print("Processing mail: ", mail_id_str)
    status, msg_data = mail.fetch(i, "(RFC822)")
    if status == 'OK' and msg_data and isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
        raw_email = msg_data[0][1]
        if not isinstance(raw_email, bytes):
            print(f"Cannot process mail {mail_id_str}: not bytes.")
            continue
        msg = email.message_from_bytes(raw_email)
    
    current_date = "Brak daty" 
    date_str = msg.get("Date")
    if date_str:
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            current_date = parsed_date.strftime("%d.%m.%Y")
        except Exception as e:
            print(f"Error parsing date for mail {mail_id_str}: {e}")
            current_date = "Nieznana data"

   
    print(f"Data maila: {current_date}")

    html = get_html(msg)
    if not html:
        continue

    text = BeautifulSoup(html, "html.parser").get_text("\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    current_job = None

    with open(Cache_file, "a") as f:
        f.write(mail_id_str + "\n")
    processed_ids.add(mail_id_str)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        l = line.lower()
        if any(s in l for s in skip):
            continue

        if "nowe oferty" in l or "właścicielem marki" in l:
            continue
        
    

        # If the line looks like a job title, we start a new job entry
        if looks_like_job(line):
            if current_job and current_job["title"]:
                clean_jobs.append(current_job)

            current_job = {
                "title": line,
                "company": None,
                "location": None,
                "salary": None,
                "date": current_date
            }
            continue

        if not current_job:
            continue

        # Filling in data for the currently found job
        if "zł" in l or "mies. " in l:
            current_job["salary"] = line
            continue
        found_city = None
        for city in ["Wrocław", "Warszawa", "Kraków", "Pietrzykowice", "Wróblowice", "Kobierzyce", "Łódź", "Poznań", "Gdańsk", "Jelcz-Laskowice", "Oleśnica", "Magnice", "Biskupice Podgórne",
                     "Krzyżanowice", "Trzebnica", "Oława", "Szczecin", "Bielany Wrocławskie", "Święte", "Długołęka", "Siechnice", "Opole", "Katowice", "Gliwice", "Rzeszów", "Brzeg Dolny"]:
            if city in line:
                found_city = city
                break
        
        if found_city:
            if any(corp in l for corp in ["sp. z o.o", " s.a", "sa ", "hays", "recruitment"]):
                    parts = line.split(found_city)
                    current_job["company"] = parts[0].strip(", ").strip()
                    current_job["location"] = found_city + parts[1]
            else:
                    current_job["location"]= line
            continue
        '''# 4. Assuming the company name 
        if current_job and current_job["company"] is None:
            # Jeśli linia zawiera "S.A." lub "Bank", to na 100% firma, a nie dalszy ciąg tytułu
            if any(e in l for e in ["s.a.", "sa.", "S.A.", "SA", "s a", "s-a", "sp. z o.o.", "sp z o.o", "sp z oo", "sp zoo", "sp. z oo", "sp z o. o.", 
                                    "sp. z o. o", "sp. zoo", "sp zoo.", "spółka z o.o.", "spolka z o.o.", "sp. z o o", "bank", "Bank", "BANK", "bank."]):
                current_job["company"] = line
            elif Knows_Companies(line):
                current_job["company"] = line
            # If the line doesn't contain "zł" and the title is very short, it's likely a continuation of the title, not the company name
            elif not found_city and "zł" not in l:
                if len(current_job["title"]) < 30:
                    current_job["title"] += " " + line
                else:
                    current_job["company"] = line'''
        

        if current_job and current_job["company"] is None:
            is_probably_company = any(e in l for e in ["s.a.", "sa.", "S.A.", "SA", "s a", "s-a", "sp. z o.o.", "sp z o.o", "sp z oo", "sp zoo", "sp. z oo", "sp z o. o.", 
                                    "sp. z o. o", "sp. zoo", "sp zoo.", "spółka z o.o.", "spolka z o.o.", "sp. z o o", "bank", "Bank", "BANK", "bank.", "spółka akcyjna", "spółka z ograniczoną odpowiedzialnością"])
            is_definitely_company = is_probably_company or Knows_Companies(line)
            if is_definitely_company:
                current_job["company"] = line
            elif not found_city and "zł" not in l:
                if len(current_job["title"]) < 20:
                    current_job["title"] += " " + line
                else:
                    current_job["company"] = line
            else:
                pass

    # Add the last job offer from the current email (if it existed)
    if current_job:
        clean_jobs.append(current_job)
  


clean_jobs_filtered = []

for job in clean_jobs:
    if is_valid_job(job):
        clean_jobs_filtered.append(job)

# Usunięcie duplikatów po tytule
#clean_jobs_filtered = list({j["title"]: j for j in clean_jobs_filtered}.values())


# Create new dataframe with new offers
new_df = pd.DataFrame(clean_jobs_filtered)

path = "new_offers.xlsx"
sheet_name = "Pracuj.pl"

jobs_saved = 0

if not new_df.empty:
    # Date as string to avoid any weird issues with Excel and sorting
    new_df['date'] = new_df['date'].astype(str)
    
    if os.path.exists(path):
        try:
            with pd.ExcelWriter(path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                try:
                    old_df = pd.read_excel(path, sheet_name=sheet_name)
                    old_df['date'] = old_df['date'].astype(str)
                    
                    df_final = pd.concat([old_df, new_df], ignore_index=True)
                except ValueError:
                    
                    df_final = new_df
                jobs_added = len(new_df)
                
                df_final['temp_date'] = pd.to_datetime(df_final['date'], format='%d.%m.%Y', errors='coerce')
                df_final = df_final.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
         
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Merged new job offers with existing data in sheet: {sheet_name}")
                
        except Exception as e:
            print("Error occurred while processing Excel file:", e)
    else:
        df_final = new_df.copy()
  
        df_final['temp_date'] = pd.to_datetime(df_final['date'], format='%d.%m.%Y', errors='coerce')
        df_final = df_final.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
        
        df_final.to_excel(path, sheet_name=sheet_name, index=False)
        jobs_added = len(df_final)
        print(f"Created new Excel file with sheet: {sheet_name}")
else:
    print("Empty list of new job offers.")

print(f"\nSaved! New unique jobs added to {sheet_name}: {jobs_added}")
print("\nFinished!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(clean_jobs))
print("FILTERED JOBS:", len(clean_jobs_filtered))