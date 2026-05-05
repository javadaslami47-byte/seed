import requests
import os
import time
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# --- تنظیمات اختصاصی شما (تکمیل شده) ---
TELEGRAM_TOKEN = '8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA'
CHAT_ID = '391754544'
ETHERSCAN_API_KEY = '8RTIQAK1ZZUNC2JNZ5EM13BCRHVZ26UA9R'

app = Flask('')
is_auto_running = False

@app.route('/')
def home():
    return "Wallet Generator & Scanner is Active!"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload)
    except:
        pass

def check_blockchain(address):
    # چک کردن تاریخچه تراکنش‌ها در شبکه اتریوم
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=1&sort=desc&apikey={ETHERSCAN_API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        # اگر وضعیت 1 باشد یعنی تراکنشی یافت شده است
        if res['status'] == '1' and len(res['result']) > 0:
            return True
    except:
        pass
    return False

def generate_and_check():
    # ۱. ساخت عبارت ۱۲ کلمه‌ای استاندارد
    mnemo = Mnemonic("english")
    words = mnemo.generate(strength=128)
    
    # ۲. استخراج آدرس اتریوم
    Account.enable_unaudited_hdwallet_features()
    acc = Account.from_mnemonic(words)
    addr = acc.address
    
    # ۳. بررسی در بلاکچین
    has_tx = check_blockchain(addr)
    return words, addr, has_tx

def auto_worker():
    global is_auto_running
    send_telegram("🚀 **جستجوی خودکار در بلاکچین شروع شد...**\nدر صورت یافتن کیف پول فعال، اطلاع داده می‌شود.")
    
    while is_auto_running:
        try:
            words, addr, has_tx = generate_and_check()
            
            # فقط اگر تراکنشی پیدا شد پیام بده
            if has_tx:
                msg = (f"💰 **کیف پول با سابقه تراکنش پیدا شد!**\n\n"
                       f"📝 کلمات بازیابی:\n`{words}`\n\n"
                       f"📍 آدرس:\n`{addr}`\n\n"
                       f"🔗 [مشاهده در ایتر اسکن](https://etherscan.io/address/{addr})")
                send_telegram(msg)
            
            # وقفه کوتاه برای رعایت محدودیت API (5 درخواست در ثانیه)
            time.sleep(1) 
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(5)

def bot_listener():
    global is_auto_running
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}"
            updates = requests.get(url).json()
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
                                send_telegram("🔄 ربات در حال حاضر در حال جستجو است...")
                        
                        elif msg_text == "/stop":
                            is_auto_running = False
                            send_telegram("🛑 عملیات جستجو متوقف شد.")
                        
                        elif msg_text == "/check":
                            send_telegram("🔎 در حال بررسی یک مورد تصادفی...")
                            words, addr, has_tx = generate_and_check()
                            status = "✅ دارای تراکنش" if has_tx else "❌ بدون تراکنش"
                            send_telegram(f"کلمات: `{words}`\n\nآدرس: `{addr}`\nوضعیت: {status}")
        except:
            time.sleep(5)
        time.sleep(1)

if __name__ == "__main__":
    # اجرای سیستم دریافت دستورات در پس‌زمینه
    Thread(target=bot_listener).start()
    
    # اجرای وب‌سرور برای زنده نگه داشتن در Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)