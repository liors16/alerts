import requests
import datetime
import time
import json
import os
from twilio.rest import Client
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()  # Load .env variables

# === Credentials from .env ===
ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
FROM_WHATSAPP = os.getenv("FROM_WHATSAPP")
TO_WHATSAPP = os.getenv("TO_WHATSAPP")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAILS = os.getenv("RECEIVER_EMAILS", "").split(",")

API_URL = os.getenv("API_URL")

SEEN_FILE = "seen.json"
seen = set()

def load_or_initialize_seen():
    global seen
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen = set(json.load(f))
        print(f"📂 Loaded {len(seen)} ads from {SEEN_FILE}")
    else:
        print("🛑 First run: saving existing ads...")
        res = requests.get(API_URL)
        data = res.json()
        listings = data.get("data", {}).get("markers", [])
        seen.update(f"https://www.yad2.co.il/item/{item['token']}" for item in listings if "token" in item)
        save_seen()
        print(f"💾 Saved {len(seen)} existing ads")

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECEIVER_EMAILS)
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            print("✅ Email sent to:", RECEIVER_EMAILS)
    except Exception as e:
        print("❌ Email error:", e)

def check_yad2_json():
    try:
        print(f"[{datetime.datetime.now()}] 📡 Checking for new ads...")
        res = requests.get(API_URL)
        data = res.json()
        listings = data.get("data", {}).get("markers", [])
        found = 0

        for item in listings:
            token = item.get("token")
            if not token:
                continue
            full_url = f"https://www.yad2.co.il/item/{token}"

            if full_url not in seen:
                seen.add(full_url)
                save_seen()
                found += 1
                price = item.get("price")
                rooms = item.get("additionalDetails", {}).get("roomsCount")
                street = item.get("address", {}).get("street", {}).get("text", "לא ידוע")

                message = f"🔔 דירה חדשה ביד2!\nרחוב: {street}\nחדרים: {rooms}\nמחיר: {price} ₪\n{full_url}"

                print("📲 Sending WhatsApp:", message)
                client.messages.create(from_=FROM_WHATSAPP, body=message, to=TO_WHATSAPP)
                send_email("🔔 דירה חדשה ביד2", message)

        print(f"✅ Added {found} new ads. Total seen: {len(seen)}")

    except Exception as e:
        print("❌ Error checking Yad2:", e)

load_or_initialize_seen()
while True:
    check_yad2_json()
    time.sleep(120)
