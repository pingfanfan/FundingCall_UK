#!/usr/bin/env python3
"""Utility script to schedule the daily scraping routine."""

import argparse
import time
from datetime import datetime, timezone

from loguru import logger

from update_all import FundingDataUpdater


def run_update() -> bool:
    updater = FundingDataUpdater()
    success = updater.update_all()
    if success:
        logger.info("Daily update finished successfully")
    else:
        logger.error("Daily update encountered errors")
    return success


def sleep_until_next_run(interval_hours: float) -> None:
    seconds = max(interval_hours * 3600, 60)
    logger.info(f"Sleeping for {interval_hours} hours before the next run...")
    time.sleep(seconds)


def main():
    parser = argparse.ArgumentParser(description="Run funding scrapers on a schedule")
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=24.0,
        help="Interval in hours between runs when --run-once is not provided (default: 24)",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Execute the update a single time and exit",
    )

    args = parser.parse_args()

    if args.run_once:
        run_update()
        return

    logger.info("Starting continuous update loop")
    while True:
        start = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        logger.info(f"Starting scheduled update at {start}")
        run_update()
        sleep_until_next_run(args.interval_hours)

if __name__ == "__main__":
    main()
