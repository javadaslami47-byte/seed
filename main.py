import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# تنظیمات لاگ برای رندر
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletEngine:
    def __init__(self):
        # تنظیمات توکن و کلیدهای شما (جایگذاری شده)
        self.tg_token = "8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA" 
        self.chat_id = "391754544"
        self.eth_key = "8RTIQAK1ZZUNC2JNZ5EM13BCRHVZ26UA9R"
        
        self.total_checked = 0
        self.session = requests.Session()
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        """ارسال پیام به تلگرام"""
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except Exception as e:
            logger.error(f"خطای تلگرام: {e}")

    def scanner_loop(self):
        logger.info("🚀 نسخه جدید شروع به کار کرد - آدرس API اصلاح شد")
        while True:
            try:
                # تولید ولت
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # اصلاح آدرس API (این بخش در کد قبلی شما غلط بود)
                url = (f"https://etherscan.io"
                       f"&address={acc.address}&tag=latest&apikey={self.eth_key}")
                
                response = self.session.get(url, timeout=15)
                data = response.json()

                # مدیریت محدودیت تعداد درخواست
                if "Max rate limit reached" in str(data.get("result")):
                    time.sleep(30)
                    continue

                # بررسی موجودی
                if data.get('status') == '1':
                    balance = int(data.get('result', 0))
                    if balance > 0:
                        self._notify(f"💎 **کیف پول پیدا شد!**\nکلمات: `{words}`\nآدرس: `{acc.address}`\nموجودی: {balance/10**18} ETH")
                
                self.total_checked += 1
                if self.total_checked % 100 == 0:
                    logger.info(f"وضعیت: {self.total_checked} ولت چک شد.")

                time.sleep(1.5) 
            except Exception as e:
                logger.error(f"خطای اسکنر: {e}")
                time.sleep(10)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    # برای بیدار نگه داشتن توسط UptimeRobot
    return {"status": "online", "checked": engine.total_checked}, 200

if __name__ == "__main__":
    # شروع ترد اسکنر
    Thread(target=engine.scanner_loop, daemon=True).start()
    # اجرای وب‌سرور
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
