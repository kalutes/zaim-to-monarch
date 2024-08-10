import datetime
import os

from currency_converter import CurrencyConverter
from dateutil.relativedelta import relativedelta

from .pyzaim import ZaimCrawler


def get_zaim_data(start_date, end_date):
    zaim_crawler = ZaimCrawler(
        os.getenv("ZAIM_USERNAME"),
        os.getenv("ZAIM_PASSWORD"),
        poor=True,
    )

    converter = CurrencyConverter()
    zaim_data = {}

    zaim_balances = zaim_crawler.get_account_balances()

    for account_name, balance in zaim_balances.items():
        zaim_data[account_name] = {}
        zaim_data[account_name]["balance"] = converter.convert(
            balance, "JPY", "USD"
        )
        zaim_data[account_name]["transactions"] = []

    current_batch_date = datetime.date(
        year=start_date.year, month=start_date.month, day=1
    )

    while current_batch_date < end_date:

        transactions = zaim_crawler.get_data(
            current_batch_date.year, current_batch_date.month
        )

        for transaction in transactions:

            transaction_date = transaction["date"].date()

            if transaction_date < start_date or transaction_date > end_date:
                continue

            try:
                converted_amount = converter.convert(
                    transaction["amount"], "JPY", "USD", transaction_date
                )
            except:
                converted_amount = converter.convert(
                    transaction["amount"], "JPY", "USD"
                )

            account_name = ""

            if "from_account" in transaction:
                converted_amount *= -1
                account_name = transaction["from_account"]
            else:
                account_name = transaction["to_account"]

            transaction["amount"] = converted_amount

            zaim_data[account_name]["transactions"].append(transaction)

        current_batch_date += relativedelta(months=1)

    return zaim_data
