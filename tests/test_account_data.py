from currency_converter import CurrencyConverter
import datetime as dt
from dateutil.relativedelta import relativedelta

from zaim_to_monarch import Account, Amount, Day, Transaction


def test_amount_usd() -> None:
    amount: Amount = Amount(usd=1)

    assert amount.usd == 1
    assert amount.jpy > 0


def test_amount_jpy() -> None:
    amount: Amount = Amount(jpy=150)

    assert amount.jpy == 150
    assert amount.usd > 0


def test_amount_jpy_usd() -> None:
    amount: Amount = Amount(jpy=150, usd=1)

    assert amount.jpy == 150
    assert amount.usd == 1


def test_amount_usd_invalid_date_does_not_throw() -> None:
    tomorrow: dt.datetime.date = dt.datetime.today() + relativedelta(days=1)
    amount: Amount = Amount(usd=1, date=tomorrow)

    assert amount.usd == 1
    assert amount.jpy != 0


def test_amount_jpy_invalid_date_does_not_throw() -> None:
    tomorrow: dt.datetime.date = dt.datetime.today() + relativedelta(days=1)
    amount: Amount = Amount(jpy=100, date=tomorrow)

    assert amount.jpy == 100
    assert amount.usd != 0


def test_account_add_first_transaction() -> None:
    account: Account = Account(
        name="account", id="id", balance=Amount(usd=1), years={}
    )

    transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=4, day=12).date(),
        merchant="nowhere",
        amount=Amount(usd=1, jpy=150),
        zaim_id="zaim id",
        monarch_id="monarch_id",
    )

    account.add_transaction(transaction)

    assert len(account.years) == 1
    assert 2020 in account.years

    year = account.years[2020]
    assert year.year == 2020
    assert len(year.months) == 1
    assert 4 in year.months

    month = year.months[4]
    assert month.month == 4
    assert len(month.days) == 1
    assert 12 in month.days

    day = month.days[12]
    assert day.day == 12
    assert len(day.transactions) == 1
    assert day.transactions[0] == transaction


def test_add_matching_zaim_id() -> None:
    day: Day = Day(day=4, transactions=[])

    transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="nowhere",
        amount=Amount(usd=1, jpy=150),
        zaim_id="zaim id",
    )

    same_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="different merchant",
        amount=Amount(usd=2, jpy=250),
        zaim_id="zaim id",
    )

    day.add_transaction(transaction)
    assert len(day.transactions) == 1
    day.add_transaction(same_transaction)
    assert len(day.transactions) == 1
    assert day.transactions[0] == transaction


def test_add_matching_monarch_id() -> None:
    day: Day = Day(day=4, transactions=[])

    transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="nowhere",
        amount=Amount(usd=1, jpy=150),
        monarch_id="monarch id",
    )

    same_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="different merchant",
        amount=Amount(usd=2, jpy=250),
        monarch_id="monarch id",
    )

    day.add_transaction(transaction)
    assert len(day.transactions) == 1
    day.add_transaction(same_transaction)
    assert len(day.transactions) == 1
    assert day.transactions[0] == transaction


def test_add_no_ids_same_amount_jpy_updates() -> None:
    day: Day = Day(day=4, transactions=[])

    transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="nowhere",
        amount=Amount(usd=1, jpy=150),
        zaim_id="zaim id",
        monarch_id="monarch id",
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="different merchant",
        amount=Amount(usd=1, jpy=150),
    )

    day.add_transaction(transaction)
    assert len(day.transactions) == 1
    day.add_transaction(new_transaction)
    assert len(day.transactions) == 1
    assert day.transactions[0].merchant == new_transaction.merchant
    assert day.transactions[0].needs_push_to_monarch


def test_add_zaim_id_to_missing_zaim_id_updates() -> None:
    day: Day = Day(day=4, transactions=[])

    transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="correct merchant",
        amount=Amount(usd=1, jpy=150),
        zaim_id="",
        monarch_id="monarch id",
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=1, day=4).date(),
        merchant="wrong merchant",
        amount=Amount(usd=1, jpy=150),
        zaim_id="zaim id",
        monarch_id="",
    )

    day.add_transaction(transaction)
    assert len(day.transactions) == 1
    day.add_transaction(new_transaction)
    assert len(day.transactions) == 1
    assert day.transactions[0].merchant == transaction.merchant
    assert day.transactions[0].zaim_id == new_transaction.zaim_id
    assert day.transactions[0].needs_push_to_monarch
