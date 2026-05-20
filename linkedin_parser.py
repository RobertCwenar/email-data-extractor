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