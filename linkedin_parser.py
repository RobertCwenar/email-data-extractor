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

load_dotenv

#Login to wp.pl
mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
login_email = os.getenv("EMAIL").strip().replace(",", "")
my_password = os.getenv("PASSWORD").strip().replace(",", "")
print("Logging in: ", bool (login_email))
print("Password loaded:", bool(my_password))

mail.login(login_email, my_password)
mail.select("inbox") # Change to the desired mailbox (e.g., "inbox")!!!!
status, messages = mail.search(None, "ALL")
mail_ids = messages[0].split()

print("Number of mails:", len(mail_ids))

# Create empty list to store data

data = []

def get_html(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/html" and "attachment" not in content_disposition:
                return part.get_payload(decode=True)
    else:
        if msg.get_content_type() == "text/html":
            return msg.get_payload(decode=True)
    return None

def clean_text(block):
    cleaned= []

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

def looks_like_job_offer(title):
    title = title.lower()

    words = [
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
        "manager", 
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

    if any (word in title for word in words):
        if not any (e in title for e in exclude):
                return True
    return False    