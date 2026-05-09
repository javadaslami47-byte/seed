# main.py
import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

logging.basicConfig(level=logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

class WalletEngine:
    def __init__(self):
        self.tg_token = os.environ.get("TG_TOKEN", "")
        self.chat_id = os.environ.get("CHAT_ID", "")
        self.eth_key = os.environ.get("ETH_KEY", "")
        
        self.is_active = False
        self.total_checked = 0
        self.start_time = time.time()
        self.session = requests.Session()
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        try:
            self.session.post(url, data={
                'chat_id': self.chat_id, 
                'text': text, 
                'parse_mode': 'Markdown'
            }, timeout=10)
        except Exception as e:
            logging.error(f"Telegram notify error: {e}")

    def _check_blockchain(self, address):
        try:
            url = (f"https://api.etherscan.io/api?module=account&action=balance"
                   f"&address={address}&tag=latest&apikey={self.eth_key}")
            resp = self.session.get(url, timeout=12).json()
            if resp.get('status') == '1':
                balance = int(resp.get('result', 0))
                if balance > 0:
                    return True, f"{balance / 10**18} ETH"

            tx_url = (f"https://api.etherscan.io/api?module=account&action=txlist"
                      f"&address={address}&startblock=0&endblock=99999999"
                      f"&page=1&offset=10&sort=desc&apikey={self.eth_key}")
            tx_resp = self.session.get(tx_url, timeout=12).json()
            if tx_resp.get('status') == '1' and tx_resp.get('result'):
                if len(tx_resp.get('result')) > 0:
                    return True, "History Found"
        except Exception as e:
            logging.error(f"Blockchain check error: {e}")
        return False, None

    def scanner_loop(self):
        while True:
            if self.is_active:
                try:
                    words = self.mnemo.generate(strength=128)
                    acc = Account.from_mnemonic(words)
                    found, details = self._check_blockchain(acc.address)
                    if found:
                        msg = (f"💎 **High Value Wallet Detected!**\n\n"
                               f"🗝 **Seed:** `{words}`\n\n"
                               f"📍 **Addr:** `{acc.address}`\n"
                               f"💰 **Status:** {details}\n\n"
                               f"🔗 [Etherscan](https://etherscan.io/address/{acc.address})")
                        self._notify(msg)
                    self.total_checked += 1
                    time.sleep(1.1)
                except Exception as e:
                    logging.error(f"Scanner loop error: {e}")
                    time.sleep(15)
            else:
                time.sleep(5)

    def control_center(self):
        offset = 0
        while True:
            try:
                url = f"https://api.telegram.org/bot{self.tg_token}/getUpdates?offset={offset}&timeout=25"
                updates = self.session.get(url, timeout=30).json()
                for update in updates.get('result', []):
                    offset = update['update_id'] + 1
                    if 'message' in update:
                        text = update['message'].get('text', '')
                        uid = str(update['message'].get('chat', {}).get('id', ''))
                        if uid == self.chat_id:
                            if text == "/start":
                                self.is_active = True
                                self._notify("🚀 **Core Engine:** Started\n**Mode:** Silent Search")
                            elif text == "/stop":
                                self.is_active = False
                                self._notify("🛑 **Core Engine:** Suspended")
                            elif text == "/stat":
                                uptime = int((time.time() - self.start_time) / 3600)
                                self._notify(f"📊 **System Status:**\n"
                                           f"Uptime: {uptime} hours\n"
                                           f"Checked: {self.total_checked}\n"
                                           f"Engine: {'Running' if self.is_active else 'Idle'}")
            except Exception as e:
                logging.error(f"Control center error: {e}")
                time.sleep(10)
            time.sleep(1)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def health():
    return f"Active:{engine.is_active}|Count:{engine.total_checked}", 200

if __name__ == "__main__":
    t1 = Thread(target=engine.scanner_loop, daemon=True)
    t2 = Thread(target=engine.control_center, daemon=True)
    t1.start()
    t2.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
