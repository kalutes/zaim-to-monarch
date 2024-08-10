import argparse
import asyncio
import datetime
import zaim_to_monarch

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(
        description="Sync zaim data to monarch money."
    )

    parser.add_argument(
        "start_date",
        type=lambda d: datetime.datetime.strptime(d, "%Y-%m-%d").date(),
        help="The starting date from which to sync transactions.",
    )

    parser.add_argument(
        "end_date",
        type=lambda d: datetime.datetime.strptime(d, "%Y-%m-%d").date(),
        help="The end date from which to sync transactions.",
    )

    args = parser.parse_args()

    load_dotenv()

    if args.end_date < args.start_date:
        print("Start date cannot be after end date.")
        return 1

    asyncio.run(zaim_to_monarch.do_sync(args.start_date, args.end_date))


if __name__ == "__main__":
    main()
