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
        # تنظیمات تلگرام شما
        self.tg_token = "8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA" 
        self.chat_id = "391754544"
        
        self.total_checked = 0
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()
        self.session = requests.Session()
        
        # استفاده از RPC رایگان Cloudflare (بدون نیاز به کلید API)
        self.rpc_url = "https://cloudflare-eth.com"

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except: pass

    def get_balance(self, address):
        """چک کردن موجودی از طریق RPC به جای API"""
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1
        }
        try:
            resp = self.session.post(self.rpc_url, json=payload, timeout=10)
            data = resp.json()
            # موجودی به صورت Hex برمی‌گردد
            hex_bal = data.get('result', '0x0')
            return int(hex_bal, 16)
        except:
            return 0

    def scanner_loop(self):
        logger.info("🚀 Scanner started using Cloudflare RPC (No API Key needed)")
        while True:
            try:
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                balance_wei = self.get_balance(acc.address)
                
                if balance_wei > 0:
                    eth_val = balance_wei / 10**18
                    self._notify(f"💎 **FOUND!**\nSeed: `{words}`\nAddr: `{acc.address}`\nBal: {eth_val} ETH")
                
                self.total_checked += 1
                if self.total_checked % 100 == 0:
                    logger.info(f"Status: {self.total_checked} wallets checked.")
                
                # وقفه بسیار کوتاه چون RPC محدودیت کمتری دارد
                time.sleep(0.5) 
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(10)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "running", "checked": engine.total_checked, "provider": "Cloudflare RPC"}, 200

if __name__ == "__main__":
    Thread(target=engine.scanner_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
