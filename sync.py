import asyncio
import os
import logging
import schedule
import time

from currency_converter import CurrencyConverter
from dotenv import load_dotenv
from monarchmoney.monarchmoney import MonarchMoney
from pyzaim.pyzaim import ZaimCrawler


async def push_to_monarch(zaim_accounts):
    mm = MonarchMoney()

    await mm.login(os.getenv("MONARCH_USERNAME"), os.getenv("MONARCH_PASSWORD"))

    mm_accounts = await mm.get_accounts()

    for zaim_account_name, zaim_account_balance in zaim_accounts.items():
        updated = False
        for mm_account in mm_accounts["accounts"]:
            if mm_account["displayName"] == zaim_account_name:
                print(
                    f"Found matching monarch account for zaim account {zaim_account_name}. Updating balance to: ${zaim_account_balance}"
                )
                await mm.update_account(
                    account_id=mm_account["id"], account_balance=zaim_account_balance
                )
                updated = True
                break

        # If a matching account was not found in monarch, create a new one.
        if not updated:
            print(
                f"No matching monarch account found for {zaim_account_name}. Creating new account and setting balance to ${zaim_account_balance}"
            )

            account_type = "depository"
            account_subtype = "checking"
            # Very naive way to determine if this is a credit card or bank account.
            if zaim_account_balance < 0:
                account_type = "credit"
                account_subtype = "credit_card"

            await mm.create_manual_account(
                account_type=account_type,
                account_sub_type=account_subtype,
                is_in_net_worth=True,
                account_name=zaim_account_name,
                account_balance=zaim_account_balance,
            )


def convert_to_usd(zaim_accounts):
    converter = CurrencyConverter()

    converted_accounts = {}

    for zaim_account_name, zaim_account_balance in zaim_accounts.items():
        converted_accounts[zaim_account_name] = converter.convert(
            zaim_account_balance, "JPY", "USD"
        )

    return converted_accounts


def get_zaim_balances():
    crawler = ZaimCrawler(
        os.getenv("ZAIM_USERNAME"),
        os.getenv("ZAIM_PASSWORD"),
        poor=True,
    )

    zaim_balances = crawler.get_account_balances()

    crawler.close()

    for zaim_account_name, zaim_account_balance in zaim_balances.items():
        print(f"Found account {zaim_account_name}: ¥{zaim_account_balance}")

    return zaim_balances


def update_balances():
    print("Syncing account balances.")

    zaim_balances = convert_to_usd(get_zaim_balances())

    asyncio.run(push_to_monarch(zaim_balances))

    print("Sync complete.")


def main():
    logging.basicConfig(level=logging.ERROR)

    load_dotenv()

    update_balances()

    schedule.every().hour.do(update_balances)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
