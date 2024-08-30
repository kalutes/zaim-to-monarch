import datetime as dt
import os
import re
import subprocess

from .account_data import Account, Amount, Transaction


class PdfParser:
    _TRANSACTION_REGEX = re.compile(
        r"^(?P<date>\d\d/\d\d/\d\d)(?P<merchant>.*)JPY(?P<amount>.*\.\d\d).*"
    )

    def __init__(self, account_name: str):
        self._account: Account = Account(
            name=account_name, id="", balance=None, years={}
        )

    def get_account(self) -> Account:
        return self._account

    def parse_dir(self, directory) -> None:

        for filename in os.listdir(directory):
            if not filename.endswith(".pdf"):
                continue

            f = os.path.join(directory, filename)

            abs_filename = os.fsdecode(os.path.abspath(f))

            self.parse_file(abs_filename)

    def parse_file(self, filename) -> None:
        pdf_to_text_args = [
            "pdftotext",
            "-layout",
            "-q",
            filename,
            "-",
        ]

        txt = subprocess.check_output(pdf_to_text_args, universal_newlines=True)
        lines = txt.splitlines()

        for line in lines:
            match = self._TRANSACTION_REGEX.search(line)

            if not match:
                continue

            try:
                date: dt.date = dt.datetime.strptime(
                    match["date"], "%y/%m/%d"
                ).date()
                merchant: str = match["merchant"].lstrip().rstrip()
                amount_jpy: float = -1 * float(
                    match["amount"].strip().replace(",", "").replace("‑", "-")
                )

                self._account.add_transaction(
                    Transaction(
                        date,
                        merchant,
                        Amount(jpy=amount_jpy, date=date),
                    )
                )
            except:
                print(f"Error when parsing file: {filename}")
                print(f"Line has bad format: {line}")
                raise
