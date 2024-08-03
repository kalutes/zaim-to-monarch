import os

from dotenv import load_dotenv
from pyzaim.pyzaim import ZaimCrawler

load_dotenv()

crawler = ZaimCrawler(
    os.getenv("ZAIM_USERNAME"),
    os.getenv("ZAIM_PASSWORD"),
    headless=False)

balances = crawler.get_account_balances()

print(balances)

crawler.close()
