import datetime as dt
import os

from typing import Dict

from dateutil.relativedelta import relativedelta

from .account_data import Account, Amount, Transaction
from .pyzaim import ZaimCrawler


class Zaim:
    def __init__(self):
        self._accounts: Dict[str, Account] = {}
        self._crawler: ZaimCrawler = ZaimCrawler(
            os.getenv("ZAIM_USERNAME"),
            os.getenv("ZAIM_PASSWORD"),
            poor=True,
        )

        balances = self._crawler.get_account_balances()

        for account_name, balance_jpy in balances.items():
            self._accounts[account_name] = Account(
                account_name, "", Amount(jpy=balance_jpy), {}
            )

    def load_data(
        self, start_date: dt.datetime.date, end_date: dt.datetime.date
    ) -> None:

        current_batch_date = dt.date(
            year=start_date.year, month=start_date.month, day=1
        )

        while current_batch_date < end_date:

            transactions = self._crawler.get_data(
                current_batch_date.year, current_batch_date.month
            )

            for transaction in transactions:

                transaction_date = transaction["date"].date()

                if transaction_date < start_date or transaction_date > end_date:
                    continue

                amount_jpy = transaction["amount"]

                if "from_account" in transaction:
                    amount_jpy *= -1
                    account_name = transaction["from_account"]
                else:
                    account_name = transaction["to_account"]

                self._accounts[account_name].add_transaction(
                    Transaction(
                        date=transaction_date,
                        merchant=transaction["place"],
                        amount=Amount(jpy=amount_jpy, date=transaction_date),
                        zaim_id=transaction["id"],
                    )
                )

            current_batch_date += relativedelta(months=1)

    def accounts(self) -> Dict[str, Account]:
        return self._accounts
