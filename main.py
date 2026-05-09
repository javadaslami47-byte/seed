import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# تنظیمات دقیق لاگ برای ردیابی در داشبورد رندر
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletEngine:
    def __init__(self):
        self.tg_token = os.environ.get("TG_TOKEN", "")
        self.chat_id = os.environ.get("CHAT_ID", "")
        self.eth_key = os.environ.get("ETH_KEY", "")
        
        self.total_checked = 0
        self.is_active = True
        self.session = requests.Session()
        # بهینه سازی کانکشن برای جلوگیری از Connection Reset
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
        self.session.mount('https://', adapter)
        
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except Exception as e:
            logger.error(f"Telegram Notify Error: {e}")

    def scanner_loop(self):
        logger.info("🚀 Scanner Loop Started")
        while True:
            try:
                # ایجاد کیف پول
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # چک کردن موجودی با هندل کردن خطاها
                url = f"https://etherscan.io{acc.address}&tag=latest&apikey={self.eth_key}"
                
                response = self.session.get(url, timeout=15)
                data = response.json()

                # اگر API محدودیت داد، بیشتر صبر کن
                if data.get("result") == "Max rate limit reached":
                    logger.warning("Rate limit hit! Sleeping for 30s...")
                    time.sleep(30)
                    continue

                if data.get('status') == '1':
                    balance = int(data.get('result', 0))
                    if balance > 0:
                        msg = f"💰 **Wallet Found!**\n\nSeed: `{words}`\nAddr: `{acc.address}`\nBal: {balance/10**18} ETH"
                        self._notify(msg)
                
                self.total_checked += 1
                
                # گزارش وضعیت هر 100 تست در لاگ رندر
                if self.total_checked % 100 == 0:
                    logger.info(f"Status Check: {self.total_checked} wallets scanned...")

                # وقفه حیاتی برای جلوگیری از کرش در رندر (پلن رایگان)
                time.sleep(2) 

            except Exception as e:
                logger.error(f"Scanner Critical Error: {e}")
                time.sleep(20) # اگر اینترنت قطع شد یا خطایی داد، 20 ثانیه صبر کن

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    # پاسخ سریع به کرون جاب برای اینکه تایم اوت ندهد
    return {
        "status": "active",
        "wallets_scanned": engine.total_checked,
        "msg": "KeepAlive Received"
    }, 200

if __name__ == "__main__":
    # اجرای اسکنر در ترد پس‌زمینه
    t = Thread(target=engine.scanner_loop, daemon=True)
    t.start()
    
    # تنظیمات پورت برای رندر
    port = int(os.environ.get("PORT", 8080))
    # غیرفعال کردن reloader برای جلوگیری از اجرای دوباره تردها
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
