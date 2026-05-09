import requests
import time
import os
import logging
from threading import Thread
from flask import Flask
from eth_account import Account
from mnemonic import Mnemonic

# Optimized logging for Render Dashboard
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletEngine:
    def __init__(self):
        # --- FULLY INTEGRATED CREDENTIALS ---
        self.tg_token = "8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA" 
        self.chat_id = "391754544"
        self.eth_key = "8RTIQAK1ZZUNC2JNZ5EM13BCRHVZ26UA9R"
        # ------------------------------------
        
        self.total_checked = 0
        self.session = requests.Session()
        # Stable connection pooling
        adapter = requests.adapters.HTTPAdapter(pool_connections=15, pool_maxsize=15)
        self.session.mount('https://', adapter)
        
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        """Sends immediate Telegram alerts"""
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            resp = self.session.post(url, json={
                'chat_id': self.chat_id, 
                'text': text, 
                'parse_mode': 'Markdown'
            }, timeout=15)
            logger.info(f"Telegram Alert Sent: {resp.status_code}")
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    def scanner_loop(self):
        """The core scanning logic"""
        logger.info("🚀 System Online. Scanning Ethereum network...")
        while True:
            try:
                # 1. Generate Mnemonic & Address
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # 2. Check Balance via Etherscan API
                url = (f"https://etherscan.io"
                       f"&address={acc.address}&tag=latest&apikey={self.eth_key}")
                
                response = self.session.get(url, timeout=15)
                data = response.json()

                # Handle Rate Limiting
                if "Max rate limit reached" in str(data.get("result")):
                    logger.warning("Etherscan limit reached. Pausing 30s...")
                    time.sleep(30)
                    continue

                # 3. Detect Funds
                if data.get('status') == '1':
                    balance_wei = int(data.get('result', 0))
                    if balance_wei > 0:
                        eth_val = balance_wei / 10**18
                        msg = (f"💎 **HIGH VALUE WALLET FOUND!**\n\n"
                               f"🗝 **Seed Phrase:** `{words}`\n"
                               f"📍 **Address:** `{acc.address}`\n"
                               f"💰 **Balance:** {eth_val} ETH\n"
                               f"🔗 [View on Etherscan](https://etherscan.io{acc.address})")
                        self._notify(msg)
                        logger.info(f"!!! ALERT !!! Funds found at {acc.address}")
                
                self.total_checked += 1
                
                # Periodic Status Update in Render Logs
                if self.total_checked % 100 == 0:
                    logger.info(f"Status: {self.total_checked} wallets checked.")

                # Delay to satisfy Render's Free Tier CPU limits
                time.sleep(1.5) 

            except Exception as e:
                logger.error(f"Critical Loop Error: {e}")
                time.sleep(20)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def health_status():
    """Endpoint for Cron-Job/UptimeRobot to ping"""
    return {
        "engine": "active", 
        "total_scanned": engine.total_checked,
        "uptime_robot_status": "received"
    }, 200

if __name__ == "__main__":
    # Start Scanner in Background
    Thread(target=engine.scanner_loop, daemon=True).start()
    
    # Start Flask Web Server
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
