import requests
import os
import time
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# --- تنظیمات اختصاصی شما ---
TELEGRAM_TOKEN = '8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA'
CHAT_ID = '391754544'
ETHERSCAN_API_KEY = '8RTIQAK1ZZUNC2JNZ5EM13BCRHVZ26UA9R'

# غیرفعال کردن گزارش‌های اضافی Flask در کنسول برای جلوگیری از خطای Output too large
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')
is_auto_running = False

@app.route('/')
def home():
    return "Bot is running silently..."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def check_blockchain(address):
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=1&sort=desc&apikey={ETHERSCAN_API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get('status') == '1' and res.get('result'):
            return True
    except:
        pass
    return False

def generate_and_check():
    mnemo = Mnemonic("english")
    words = mnemo.generate(strength=128)
    Account.enable_unaudited_hdwallet_features()
    acc = Account.from_mnemonic(words)
    has_tx = check_blockchain(acc.address)
    return words, acc.address, has_tx

def auto_worker():
    global is_auto_running
    send_telegram("✅ **نسخه بهینه فعال شد.** جستجو در جریان است...")
    while is_auto_running:
        try:
            words, addr, has_tx = generate_and_check()
            if has_tx:
                msg = (f"💰 **کیف پول یافت شد!**\n\n"
                       f"📝 کلمات:\n`{words}`\n\n"
                       f"📍 آدرس:\n`{addr}`\n\n"
                       f"🔗 [Etherscan](https://etherscan.io/address/{addr})")
                send_telegram(msg)
            # ایجاد وقفه برای جلوگیری از فشار به سرور و محدودیت API
            time.sleep(1.2) 
        except:
            time.sleep(10)

def bot_listener():
    global is_auto_running
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=30"
            updates = requests.get(url, timeout=40).json()
            for update in updates.get('result', []):
                offset = update['update_id'] + 1
                if 'message' in update:
                    msg_text = update['message'].get('text', '')
                    user_id = str(update['message'].get('chat', {}).get('id', ''))
                    if user_id == CHAT_ID:
                        if msg_text == "/start":
                            if not is_auto_running:
                                is_auto_running = True
                                Thread(target=auto_worker).start()
                            else:
                                send_telegram("در حال جستجو...")
                        elif msg_text == "/stop":
                            is_auto_running = False
                            send_telegram("🛑 متوقف شد.")
        except:
            time.sleep(5)
        time.sleep(1)

if __name__ == "__main__":
    Thread(target=bot_listener, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    # اجرای Flask بدون چاپ لاگ در کنسول
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
