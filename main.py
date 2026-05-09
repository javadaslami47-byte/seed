import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletEngine:
    def __init__(self):
        # دریافت متغیرها از پنل رندر
        self.tg_token = os.environ.get("TG_TOKEN", "")
        self.chat_id = os.environ.get("CHAT_ID", "")
        self.eth_key = os.environ.get("ETH_KEY", "")
        
        self.total_checked = 0
        self.session = requests.Session()
        # تنظیم مجدد برای پایداری کانکشن
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self.session.mount('https://', adapter)
        
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        # اصلاح آدرس تلگرام (اشتباه در کد شما: api.telegram.org حذف شده بود)
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            resp = self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
            logger.info(f"Telegram status: {resp.status_code}")
        except Exception as e:
            logger.error(f"Telegram Notify Error: {e}")

    def scanner_loop(self):
        logger.info("🚀 Scanner Loop Started Successfully")
        while True:
            try:
                # تولید ولت
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # اصلاح آدرس اتراسکن (اشتباه در کد شما: پارامترهای module و action حذف شده بودند)
                url = (f"https://etherscan.io"
                       f"&address={acc.address}&tag=latest&apikey={self.eth_key}")
                
                response = self.session.get(url, timeout=15)
                data = response.json()

                # مدیریت محدودیت نرخ درخواست
                if "Max rate limit reached" in str(data.get("result")):
                    logger.warning("Rate limit hit! Sleeping for 30s...")
                    time.sleep(30)
                    continue

                if data.get('status') == '1':
                    balance = int(data.get('result', 0))
                    if balance > 0:
                        msg = f"💎 **Wallet Found!**\n\nSeed: `{words}`\nAddr: `{acc.address}`\nBal: {balance/10**18} ETH"
                        self._notify(msg)
                        logger.info(f"!!! FOUND !!! {acc.address}")
                
                self.total_checked += 1
                
                # چاپ وضعیت هر 100 عدد در لاگ رندر
                if self.total_checked % 100 == 0:
                    logger.info(f"Checked: {self.total_checked} wallets...")

                # وقفه حیاتی برای پلن رایگان رندر (کمتر از 1.5 ثانیه باعث بلاک شدن می‌شود)
                time.sleep(2) 

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(15)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    # پاسخ به کرون‌جاب (مثل UptimeRobot)
    return {
        "status": "running",
        "wallets_scanned": engine.total_checked,
        "api_key_set": bool(engine.eth_key)
    }, 200

if __name__ == "__main__":
    # اجرای اسکنر
    Thread(target=engine.scanner_loop, daemon=True).start()
    
    # تنظیم پورت رندر
    port = int(os.environ.get("PORT", 8080))
    # غیرفعال کردن reloader برای جلوگیری از اجرای دو برابری تردها
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
