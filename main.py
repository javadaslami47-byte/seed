import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# Improved logging to see errors in Render Dashboard
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletEngine:
    def __init__(self):
        self.tg_token = os.environ.get("TG_TOKEN", "")
        self.chat_id = os.environ.get("CHAT_ID", "")
        self.eth_key = os.environ.get("ETH_KEY", "")
        self.app_url = os.environ.get("APP_URL", "") # Add your Render URL here
        
        self.is_active = False
        self.total_checked = 0
        self.start_time = time.time()
        self.session = requests.Session()
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, data={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    def _keep_alive(self):
        """Self-pinging mechanism to prevent Render sleeping"""
        while True:
            try:
                if self.app_url:
                    self.session.get(self.app_url, timeout=10)
                    logger.info("Self-ping successful")
            except:
                pass
            time.sleep(600) # Ping every 10 minutes

    def _check_blockchain(self, address):
        # Your existing blockchain logic...
        # Note: Ensure your Etherscan API key is valid to avoid 429 errors
        try:
            url = f"https://etherscan.io{address}&tag=latest&apikey={self.eth_key}"
            resp = self.session.get(url, timeout=12).json()
            if resp.get('result') and int(resp['result']) > 0:
                return True, f"{int(resp['result']) / 10**18} ETH"
        except Exception as e:
            logger.error(f"Etherscan Error: {e}")
        return False, None

    def scanner_loop(self):
        while True:
            if self.is_active:
                try:
                    words = self.mnemo.generate(strength=128)
                    acc = Account.from_mnemonic(words)
                    found, details = self._check_blockchain(acc.address)
                    if found:
                        msg = f"💎 **Found:** `{words}`\nAddr: `{acc.address}`"
                        self._notify(msg)
                    self.total_checked += 1
                    time.sleep(2) # Increased delay to prevent CPU spiking on Render
                except Exception as e:
                    time.sleep(10)
            else:
                time.sleep(5)

    def control_center(self):
        offset = 0
        while True:
            try:
                url = f"https://telegram.org{self.tg_token}/getUpdates?offset={offset}&timeout=20"
                updates = self.session.get(url, timeout=25).json()
                for update in updates.get('result', []):
                    offset = update['update_id'] + 1
                    msg = update.get('message', {})
                    if str(msg.get('chat', {}).get('id')) == self.chat_id:
                        text = msg.get('text')
                        if text == "/start":
                            self.is_active = True
                            self._notify("🚀 Engine Started")
                        elif text == "/stop":
                            self.is_active = False
                            self._notify("🛑 Engine Stopped")
            except:
                time.sleep(10)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def health():
    return {"status": "online", "checked": engine.total_checked, "active": engine.is_active}, 200

if __name__ == "__main__":
    # Start all threads
    Thread(target=engine.scanner_loop, daemon=True).start()
    Thread(target=engine.control_center, daemon=True).start()
    Thread(target=engine._keep_alive, daemon=True).start()
    
    port = int(os.environ.get("PORT", 8080))
    # use_reloader=False is critical for Render to prevent duplicate threads
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
