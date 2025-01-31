import datetime as dt
import os
import re

from dateutil.relativedelta import relativedelta
from typing import Dict, Optional

from .account_data import Account, Amount, Day, Month, Transaction, Year
from .monarchmoney import MonarchMoney


class Monarch:
    _TRANSACTION_LIMIT: int = 10000

    _TRANSACTION_NOTES_RE = re.compile(
        r"amount_jpy=(?P<amount_jpy>-?\d+)(,zaim_id=(?P<zaim_id>\d+))?"
    )

    _TRANSACTION_CATEGORY: str = "zaim-to-monarch"

    def __init__(self, mm=MonarchMoney()) -> None:
        self._mm: MonarchMoney = mm
        self._accounts: Dict[str, Account] = {}
        self._transaction_category_id = ""

    async def login(self) -> None:
        username = os.getenv("MONARCH_USERNAME")
        password = os.getenv("MONARCH_PASSWORD")
        mfa_key = os.getenv("MONARCH_MFA_KEY")
        await self._mm.login(username, password, mfa_secret_key=mfa_key)

        await self._get_accounts()

    async def import_account(self, incoming_account: Account) -> None:
        if not incoming_account.name in self._accounts:
            self._accounts[incoming_account.name] = Account(
                name=incoming_account.name,
                id="",
                balance=incoming_account.balance,
                years={},
            )

        monarch_account = self._accounts[incoming_account.name]

        if incoming_account.balance:
            monarch_account.balance = incoming_account.balance
            if monarch_account.id:
                await self._update_account_balance(monarch_account)

        for incoming_year in incoming_account.years.values():
            year: int = incoming_year.year

            if not year in monarch_account.years:
                monarch_account.years[year] = Year(year, {})

            monarch_account_year = monarch_account.years[year]

            for incoming_month in incoming_year.months.values():
                month: int = incoming_month.month

                if not month in monarch_account_year.months:
                    await self._pull_monarch_transactions(monarch_account, year, month)

                for incoming_day in incoming_month.days.values():
                    for incoming_transaction in incoming_day.transactions:
                        monarch_account.add_transaction(incoming_transaction)

    def accounts(self) -> Dict[str, Account]:
        return self._accounts

    async def push(self, dry_run=True) -> None:
        for account in self._accounts.values():
            if not account.id:
                print(
                    f"Creating new monarch account: {account.name} Balance: {account.balance}"
                )
                if not dry_run:
                    await self._push_new_account(account)

            for year in account.years.values():
                for month in year.months.values():
                    for day in month.days.values():
                        for transaction in day.transactions:
                            if transaction.needs_push_to_monarch:

                                await self._update_transaction(
                                    account.id, transaction, dry_run
                                )

        return

    async def _get_accounts(self) -> None:
        raw_accounts = await self._mm.get_accounts()

        for raw_account in raw_accounts["accounts"]:

            id: str = raw_account["id"]
            name: str = raw_account["displayName"]
            balance: float = raw_account["displayBalance"]

            self._accounts[name] = Account(
                name=name, id=id, balance=Amount(usd=balance), years={}
            )

    async def _push_new_account(self, account: Account) -> None:
        account_type = "depository"
        account_subtype = "checking"
        # Very naive way to determine if this is a credit card or bank account.
        if account.balance.usd < 0:
            account_type = "credit"
            account_subtype = "credit_card"

        create_account_response = await self._mm.create_manual_account(
            account_type=account_type,
            account_sub_type=account_subtype,
            is_in_net_worth=True,
            account_name=account.name,
            account_balance=account.balance.usd,
        )

        new_account_id: str = create_account_response["createManualAccount"]["account"][
            "id"
        ]

        account.id = new_account_id

    async def _update_transaction(
        self, account_id: str, transaction: Transaction, dry_run: bool
    ) -> None:
        if not dry_run:
            transaction.needs_push_to_monarch = False

        if transaction.monarch_id:
            notes: str = self._create_transaction_notes(transaction)
            print(f"Updating transaction: {transaction}")
            if not dry_run:
                await self._mm.update_transaction(
                    transaction_id=transaction.monarch_id,
                    merchant_name=transaction.merchant,
                    notes=notes,
                )
            return

        if not self._transaction_category_id:
            await self._find_transaction_category_id()

        print(f"Creating new transaction: {transaction}")

        if not dry_run:
            create_result = await self._mm.create_transaction(
                date=self._format_date(transaction.date),
                account_id=account_id,
                amount=transaction.amount.usd,
                merchant_name=transaction.merchant,
                category_id=self._transaction_category_id,
                notes=self._create_transaction_notes(transaction),
            )
            transaction.monarch_id = create_result["createTransaction"]["transaction"][
                "id"
            ]

    async def _pull_monarch_transactions(
        self, account: Account, year: int, month: int
    ) -> None:

        if not account.id:
            return

        start_date: dt.date = dt.datetime(year=year, month=month, day=1).date()
        end_date: dt.date = (start_date + relativedelta(months=1)) - relativedelta(
            days=1
        )

        raw_transactions = await self._mm.get_transactions(
            limit=self._TRANSACTION_LIMIT,
            start_date=self._format_date(start_date),
            end_date=self._format_date(end_date),
            account_ids=[account.id],
        )

        for raw_transaction in raw_transactions["allTransactions"]["results"]:
            zaim_id: str = ""
            amount_jpy: float = 0

            match = self._TRANSACTION_NOTES_RE.search(raw_transaction["notes"])
            if not match:
                print(
                    f"ERROR: Transaction notes do not match expected format: {raw_transaction['notes']}"
                )
                continue

            amount_jpy = float(match["amount_jpy"])
            if match["zaim_id"]:
                zaim_id = match["zaim_id"]

            new_transaction = Transaction(
                date=self._parse_date(raw_transaction["date"]),
                merchant=raw_transaction["merchant"]["name"],
                amount=Amount(jpy=amount_jpy, usd=raw_transaction["amount"]),
                zaim_id=zaim_id,
                monarch_id=raw_transaction["id"],
            )

            account.add_transaction(new_transaction)

    async def _update_account_balance(self, account: Account) -> None:
        await self._mm.update_account(
            account_id=account.id, account_balance=account.balance.usd
        )

    async def _find_transaction_category_id(self) -> None:
        existing_categories = await self._mm.get_transaction_categories()

        for category in existing_categories["categories"]:
            if category["name"] == self._TRANSACTION_CATEGORY:
                self._transaction_category_id = category["id"]
                return

        # Otherwise create the correct category
        existing_groups = await self._mm.get_transaction_category_groups()

        group_id_for_new_category = ""

        for group in existing_groups["categoryGroups"]:
            if group["name"] == "Other":
                group_id_for_new_category = group["id"]

        create_result = await self._mm.create_transaction_category(
            group_id=group_id_for_new_category,
            transaction_category_name=self._TRANSACTION_CATEGORY,
        )

        self._transaction_category_id = create_result["createCategory"]["category"][
            "id"
        ]

    def _create_transaction_notes(self, transaction: Transaction) -> str:
        zaim_id_str: str = ""

        if transaction.zaim_id:
            zaim_id_str = f",zaim_id={transaction.zaim_id}"

        return f"amount_jpy={int(round(transaction.amount.jpy))}{zaim_id_str}"

    def _format_date(self, date: dt.date) -> str:
        return date.strftime("%Y-%m-%d")

    def _parse_date(self, date_str: str) -> dt.date:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").date()
