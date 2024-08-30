import datetime as dt
import pytest

from zaim_to_monarch import Account, Amount, Monarch, Transaction

from .fake_monarch_money import FakeMonarchMoney

pytest_plugins = "pytest_asyncio"


@pytest.mark.asyncio
async def test_login_retrieves_accounts() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    assert fake_monarch_money.get_accounts_count == 1

    accounts = monarch.accounts()
    assert len(accounts) == 5

    assert "Savings" in accounts
    assert accounts["Savings"].id == "11111"
    assert accounts["Savings"].balance.usd == 1000

    assert "Checking" in accounts
    assert accounts["Checking"].id == "22222"
    assert accounts["Checking"].balance.usd == 2000

    assert "JP Credit Card" in accounts
    assert accounts["JP Credit Card"].id == "33333"
    assert accounts["JP Credit Card"].balance.usd == 100

    assert "JP Checking" in accounts
    assert accounts["JP Checking"].id == "44444"
    assert accounts["JP Checking"].balance.usd == 3000

    assert "JP Savings" in accounts
    assert accounts["JP Savings"].id == "55555"
    assert accounts["JP Savings"].balance.usd == 4000

    for account in accounts.values():
        assert accounts["JP Savings"].balance.jpy != 0
        assert len(account.years) == 0


@pytest.mark.asyncio
async def test_import_account_updates_balance() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    updated_account: Account = Account(
        name="JP Checking", id="", balance=Amount(usd=600), years={}
    )

    await monarch.import_account(updated_account)

    assert "44444" in fake_monarch_money.balances
    assert fake_monarch_money.balances["44444"] == 600


@pytest.mark.asyncio
async def test_import_existing_account_pulls_monthly_transactions() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="JP Checking",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=10).date(),
        merchant="Amazon",
        amount=Amount(usd=6),
        zaim_id="1234",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    assert fake_monarch_money.get_transactions_start_date == "2020-09-01"
    assert fake_monarch_money.get_transactions_end_date == "2020-09-30"
    assert fake_monarch_money.get_transactions_account_ids == ["44444"]

    assert new_account.name in monarch.accounts()

    monarch_account = monarch.accounts()[new_account.name]

    assert 2020 in monarch_account.years
    year = monarch_account.years[2020]
    assert 9 in year.months
    month = year.months[9]

    assert 19 in month.days
    day = month.days[19]

    assert len(day.transactions) == 1
    transaction = day.transactions[0]
    assert transaction.amount.jpy == 60000
    assert transaction.zaim_id == ""

    assert 16 in month.days
    day = month.days[16]
    assert len(day.transactions) == 1
    transaction = day.transactions[0]
    assert transaction.amount.jpy == 2000
    assert transaction.zaim_id == "5467"


@pytest.mark.asyncio
async def test_push_dry_run_does_not_create() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="New Account",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=10).date(),
        merchant="Amazon",
        amount=Amount(usd=6, jpy=123),
        zaim_id="1234",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    await monarch.push(dry_run=True)

    assert fake_monarch_money.create_transaction_count == 0


@pytest.mark.asyncio
async def test_push_creates_correct_transaction_category() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="New Account",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=10).date(),
        merchant="Amazon",
        amount=Amount(usd=6),
        zaim_id="1234",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    fake_monarch_money.category_exists = False

    await monarch.push(dry_run=False)

    assert (
        fake_monarch_money.new_transaction_category_group_id
        == "184504200517522266"
    )
    assert fake_monarch_money.new_transaction_category_name == "zaim-to-monarch"


@pytest.mark.asyncio
async def test_push_does_not_create_transaction_category_if_exists() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="New Account",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=10).date(),
        merchant="Amazon",
        amount=Amount(usd=6),
        zaim_id="1234",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    await monarch.push(dry_run=False)

    assert not fake_monarch_money.new_transaction_category_group_id
    assert not fake_monarch_money.new_transaction_category_name


@pytest.mark.asyncio
async def test_push_new_account_creates_account() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="New Account",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    await monarch.import_account(new_account)

    await monarch.push(dry_run=False)

    accounts = monarch.accounts()
    assert "New Account" in accounts
    new_account = accounts["New Account"]
    assert new_account.id == "new_account_id"
    assert new_account.balance.usd == 100
    assert new_account.balance.jpy != 0
    assert len(new_account.years) == 0


@pytest.mark.asyncio
async def test_push_creates_transaction_fields() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="New Account",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=10).date(),
        merchant="Amazon",
        amount=Amount(usd=6, jpy=123),
        zaim_id="1234",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    await monarch.push(dry_run=False)

    assert fake_monarch_money.create_transaction_count == 1
    assert fake_monarch_money.new_transaction_date == "2020-09-10"
    assert fake_monarch_money.new_transaction_account_id == "new_account_id"
    assert fake_monarch_money.new_transaction_amount == 6
    assert fake_monarch_money.new_transaction_merchant == "Amazon"
    assert fake_monarch_money.new_transaction_category_id == "2222"
    assert (
        fake_monarch_money.new_transaction_notes
        == "amount_jpy=123,zaim_id=1234"
    )


@pytest.mark.asyncio
async def test_push_no_new_transactions_does_not_create_update() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="New Account",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=10).date(),
        merchant="Amazon",
        amount=Amount(usd=6, jpy=123),
        zaim_id="1234",
        monarch_id="45858",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    await monarch.push(dry_run=False)

    assert fake_monarch_money.create_transaction_count == 0
    assert fake_monarch_money.update_transaction_count == 0


@pytest.mark.asyncio
async def test_push_existing_transaction_that_needs_zaim_id_update() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="JP Checking",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=19).date(),
        merchant="Amazon",
        amount=Amount(jpy=60000),
        zaim_id="1234",
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    await monarch.push(dry_run=False)

    assert fake_monarch_money.create_transaction_count == 0
    assert fake_monarch_money.update_transaction_count == 1
    assert fake_monarch_money.update_transaction_id == "11111"
    assert fake_monarch_money.update_transaction_merchant == "Capital One"
    assert (
        fake_monarch_money.update_transaction_notes
        == "amount_jpy=60000,zaim_id=1234"
    )


@pytest.mark.asyncio
async def test_push_existing_transaction_that_needs_merchant_update() -> None:
    fake_monarch_money: FakeMonarchMoney = FakeMonarchMoney()
    monarch: Monarch = Monarch(mm=fake_monarch_money)
    await monarch.login()

    new_account: Account = Account(
        name="JP Checking",
        id="1234",
        balance=Amount(usd=100),
        years={},
    )

    new_transaction: Transaction = Transaction(
        date=dt.datetime(year=2020, month=9, day=16).date(),
        merchant="McDonald's",
        amount=Amount(jpy=2000),
    )

    new_account.add_transaction(new_transaction)

    await monarch.import_account(new_account)

    await monarch.push(dry_run=False)

    assert fake_monarch_money.create_transaction_count == 0
    assert fake_monarch_money.update_transaction_count == 1
    assert fake_monarch_money.update_transaction_id == "22222"
    assert fake_monarch_money.update_transaction_merchant == "McDonald's"
    assert (
        fake_monarch_money.update_transaction_notes
        == "amount_jpy=2000,zaim_id=5467"
    )
