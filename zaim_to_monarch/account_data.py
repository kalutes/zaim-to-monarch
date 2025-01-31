from currency_converter import CurrencyConverter, ECB_URL
import dataclasses
import datetime as dt

from typing import Dict, List, Optional


class Amount:
    _converter = CurrencyConverter(
        currency_file=ECB_URL,
        fallback_on_missing_rate=True,
        fallback_on_wrong_date=True,
    )

    def __init__(
        self,
        jpy: Optional[float] = None,
        usd: Optional[float] = None,
        date: Optional[dt.date] = None,
    ) -> None:
        
        if jpy is None and usd is None:
            raise Exception("Either JPY or USD is required")

        if jpy is not None and usd is not None:
            self._jpy = jpy
            self._usd = usd
            return

        if jpy is not None:
            self._jpy = jpy
            self._usd = self._converter.convert(jpy, "JPY", "USD", date)

        if usd is not None:
            self._usd = usd
            self._jpy = self._converter.convert(usd, "USD", "JPY", date)

    @property
    def jpy(self) -> float:
        return self._jpy

    @property
    def usd(self) -> float:
        return self._usd

    def __str__(self) -> str:
        return f"(¥{round(self.jpy)}, ${round(self.usd, 2)})"


@dataclasses.dataclass(frozen=False)
class Transaction:
    date: dt.date
    merchant: str
    amount: Amount
    zaim_id: str = ""
    monarch_id: str = ""
    needs_push_to_monarch: bool = False

    def __str__(self):
        return f"Date: {self.date} Merchant: {self.merchant} Amount: {self.amount} zaim_id: {self.zaim_id} monarch_id: {self.monarch_id}"


@dataclasses.dataclass(frozen=False)
class Day:
    day: int
    transactions: List[Transaction]

    def add_transaction(self, new_transaction: Transaction) -> None:

        if not new_transaction.monarch_id:
            new_transaction.needs_push_to_monarch = True

        for transaction in self.transactions:
            if new_transaction.zaim_id and (
                transaction.zaim_id == new_transaction.zaim_id
            ):
                return

            if new_transaction.monarch_id and (
                transaction.monarch_id == new_transaction.monarch_id
            ):
                return

            # Transactions sourced from PDFs will not have any ID.
            # In this case, the merchant info may differ and cannot
            # be used to distinguish transactions. Use amount_jpy as
            # an approximate proxy for an ID.
            if not new_transaction.zaim_id and not new_transaction.monarch_id:
                if new_transaction.amount.jpy == transaction.amount.jpy:
                    transaction.merchant = new_transaction.merchant
                    transaction.amount = new_transaction.amount
                    transaction.needs_push_to_monarch = True
                    return

            # Similarly, transactions that were originally created from
            # a PDF import may have a monarch id but not a zaim id.
            # In this case, update the zaim id when a match is found.
            if (
                not transaction.zaim_id
                and new_transaction.zaim_id
                and new_transaction.amount.jpy == transaction.amount.jpy
            ):
                transaction.zaim_id = new_transaction.zaim_id
                transaction.needs_push_to_monarch = True
                return

        self.transactions.append(new_transaction)


@dataclasses.dataclass(frozen=False)
class Month:
    month: int
    days: Dict[int, Day]

    def add_transaction(self, transaction: Transaction) -> None:
        day = transaction.date.day

        if not day in self.days:
            self.days[day] = Day(day, [])

        self.days[day].add_transaction(transaction)


@dataclasses.dataclass(frozen=False)
class Year:
    year: int
    months: Dict[int, Month]

    def add_transaction(self, transaction: Transaction) -> None:
        month = transaction.date.month

        if not month in self.months:
            self.months[month] = Month(month, {})

        self.months[month].add_transaction(transaction)


@dataclasses.dataclass(frozen=False)
class Account:
    name: str
    id: str
    balance: Optional[Amount]
    years: Dict[int, Year]

    def add_transaction(self, transaction: Transaction) -> None:
        year = transaction.date.year

        if not year in self.years:
            self.years[year] = Year(year, {})

        self.years[year].add_transaction(transaction)
