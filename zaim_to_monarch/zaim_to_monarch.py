import datetime
import os
import re

from .monarchmoney import MonarchMoney
from .zaim_data import get_zaim_data


def format_time_for_monarch(date):
    return date.strftime("%Y-%m-%d")


async def login_monarch():
    mm = MonarchMoney()

    await mm.login(os.getenv("MONARCH_USERNAME"), os.getenv("MONARCH_PASSWORD"))

    return mm


def find_matching_monarch_account(monarch_accounts, zaim_account_name):
    for mm_account in monarch_accounts["accounts"]:
        if mm_account["displayName"] == zaim_account_name:
            return mm_account
    return None


async def create_new_monarch_account(monarch_session, account_name, balance):
    account_type = "depository"
    account_subtype = "checking"
    # Very naive way to determine if this is a credit card or bank account.
    if balance < 0:
        account_type = "credit"
        account_subtype = "credit_card"

    create_account_response = await monarch_session.create_manual_account(
        account_type=account_type,
        account_sub_type=account_subtype,
        is_in_net_worth=True,
        account_name=account_name,
        account_balance=balance,
    )


async def update_account_balance(
    monarch_session, account_name, new_balance, monarch_account=None
):
    # If a matching account was not found in monarch, create a new one.
    if monarch_account is None:
        print(
            f"No monarch account found for {account_name}. Creating new account and setting balance to ${new_balance}"
        )
        await create_new_monarch_account(
            monarch_session, account_name, new_balance
        )
        return

    # Otherwise update the balance of the existing account.
    print(f"Updating monarch account {account_name} balance to: ${new_balance}")

    await monarch_session.update_account(
        account_id=monarch_account["id"],
        account_balance=new_balance,
    )


async def get_existing_zaim_transactions(
    monarch_session, account_id, start_date, end_date
):
    transactions_result = await monarch_session.get_transactions(
        limit=1000000,
        start_date=format_time_for_monarch(start_date),
        end_date=format_time_for_monarch(end_date),
        account_ids=[account_id],
    )

    existing_zaim_ids = set()

    zaim_id_re = re.compile(r"zaim_id=(?P<zaim_id>\d+)")

    for transaction in transactions_result["allTransactions"]["results"]:
        if transaction["notes"]:
            match = zaim_id_re.search(transaction["notes"])
            if not match:
                continue

            existing_zaim_ids.add(match["zaim_id"])

    return existing_zaim_ids


async def get_category_id_for_monarch(monarch_session):
    existing_categories = await monarch_session.get_transaction_categories()

    for category in existing_categories["categories"]:
        if category["name"] == "zaim":
            return category["id"]

    existing_groups = await monarch_session.get_transaction_category_groups()

    group_id_for_new_category = ""

    for group in existing_groups["categoryGroups"]:
        if group["name"] == "Other":
            group_id_for_new_category = group["id"]

    if not group_id_for_new_category:
        print("Failed to find group 'Other'!")
        exit(1)

    create_result = await monarch_session.create_transaction_category(
        group_id=group_id_for_new_category, transaction_category_name="zaim"
    )

    return create_result["createCategory"]["category"]["id"]


async def create_new_monarch_transaction(
    monarch_session, monarch_account_id, monarch_category_id, zaim_transaction
):
    print(
        f"Creating new monarch transaction. {zaim_transaction['date']}: {zaim_transaction['place']} ${zaim_transaction['amount']}"
    )
    await monarch_session.create_transaction(
        date=format_time_for_monarch(zaim_transaction["date"]),
        account_id=monarch_account_id,
        amount=zaim_transaction["amount"],
        merchant_name=zaim_transaction["place"],
        category_id=monarch_category_id,
        notes=f"zaim_id={zaim_transaction['id']}",
    )


async def do_sync(start_date, end_date):
    zaim_data = get_zaim_data(start_date, end_date)

    monarch_session = await login_monarch()

    monarch_accounts = await monarch_session.get_accounts()

    for zaim_account_name in zaim_data.keys():
        monarch_account = find_matching_monarch_account(
            monarch_accounts, zaim_account_name
        )

        await update_account_balance(
            monarch_session,
            zaim_account_name,
            zaim_data[zaim_account_name]["balance"],
            monarch_account,
        )

    # New accounts may have been created when updating balances, so refresh the accounts list.
    monarch_accounts = await monarch_session.get_accounts()

    monarch_category_id = await get_category_id_for_monarch(monarch_session)

    for zaim_account_name in zaim_data.keys():
        monarch_account = find_matching_monarch_account(
            monarch_accounts, zaim_account_name
        )

        if not monarch_account:
            print(
                "Failed to find matching monarch account after balance update!"
            )
            continue

        existing_zaim_transactions = await get_existing_zaim_transactions(
            monarch_session, monarch_account["id"], start_date, end_date
        )

        for zaim_transaction in zaim_data[zaim_account_name]["transactions"]:
            if zaim_transaction["id"] in existing_zaim_transactions:
                continue

            await create_new_monarch_transaction(
                monarch_session,
                monarch_account["id"],
                monarch_category_id,
                zaim_transaction,
            )
