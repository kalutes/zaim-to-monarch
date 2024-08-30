import argparse
import asyncio
import datetime as dt
import os
import schedule
import time
import traceback
import zaim_to_monarch

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv


def sync_once(start_date: dt.date, end_date: dt.date) -> None:
    if end_date < start_date:
        print("Start date cannot be after end date.")
        return 1

    asyncio.run(zaim_to_monarch.do_sync(start_date, end_date))


def import_pdfs(pdfs_dir: str) -> None:
    asyncio.run(zaim_to_monarch.import_pdfs(pdfs_dir))


last_sync_date = dt.datetime.min


def periodic_sync_once(days_interval: int) -> None:
    global last_sync_date
    if last_sync_date == dt.datetime.min:
        last_sync_date = dt.datetime.now() - relativedelta(days=days_interval)

    try:
        # Always sync one more week than is necessary in case any delayed transactions have appeared since the last sync.
        sync_start = (last_sync_date - relativedelta(days=7)).date()
        print(f"Syncing data from {sync_start} to {dt.date.today()}")
        sync_once(sync_start, dt.date.today())
        last_sync_date = dt.date.today()
    except Exception:
        traceback.print_exc()
        print(
            "Exception occurred when syncing. Sleeping until next sync attempt."
        )


def periodic_sync(days_interval: int) -> None:
    schedule.every(days_interval).days.do(
        periodic_sync_once, days_interval=days_interval
    )

    # Running initial sync.
    schedule.run_all()

    while True:
        remaining_sleep_hours = schedule.idle_seconds() / 60 / 60
        print(f"Time until next sync: {round(remaining_sleep_hours)} hours")
        schedule.run_pending()
        time.sleep(3600)


def dir_path(path: str) -> str:
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"pdf:{path} is not a valid path")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync zaim data to monarch money."
    )

    parser.add_argument(
        "-d",
        "--date_range",
        nargs=2,
        type=lambda d: dt.datetime.strptime(d, "%Y-%m-%d").date(),
        help="--date_range <start date: YYYY-MM-DD> <end date: YYYY-MM-DD>. Immediately sync the specified date range.",
    )

    parser.add_argument(
        "-e",
        "--every_n_days",
        type=int,
        help="Automatically sync every n days. The first sync will include the past every_n_days days of data.",
    )

    parser.add_argument(
        "-p",
        "--pdf",
        type=dir_path,
        help="Parse and upload transaction data from PDFs in the specified directory.",
    )

    args = parser.parse_args()

    if not (bool(args.every_n_days) ^ bool(args.date_range) ^ bool(args.pdf)):
        print("Choose either date_range, every_n_days, or pdf.")
        return -1

    load_dotenv()

    if args.pdf:
        return import_pdfs(args.pdf)

    if args.date_range:
        return sync_once(args.date_range[0], args.date_range[1])

    return periodic_sync(args.every_n_days)


if __name__ == "__main__":
    main()
