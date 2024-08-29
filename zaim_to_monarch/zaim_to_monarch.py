import sys

from .monarch import Monarch
from .pdf_parser import PdfParser
from .zaim import Zaim


async def do_sync(start_date, end_date):

    zaim = Zaim()

    zaim.load_data(start_date, end_date)

    monarch = Monarch()
    await monarch.login()

    for zaim_account in zaim.accounts().values():
        await monarch.import_account(zaim_account)

    await monarch.push()


async def import_pdfs(pdfs_dir):
    monarch = Monarch()
    await monarch.login()

    i: int = 1

    account_ids: Dict[int, str] = {}
    for account in monarch.accounts().values():
        account_ids[i] = account.name
        print(f"{i}: {account.name}")
        i += 1

    print("Choose account for PDF import:")

    choice: int = 0
    while not choice in account_ids:
        line = input()
        try:
            choice = int(line)
        except:
            choice = 0

        if not choice in account_ids:
            print(f"{line} is not a valid choice")

    parser: PdfParser = PdfParser(account_ids[choice])

    parser.parse_dir(pdfs_dir)

    await monarch.import_account(parser.get_account())

    await monarch.push()

    return
