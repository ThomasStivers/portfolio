from configparser import ConfigParser
from pathlib import Path
from os.path import join, splitext

import pandas as pd

from portfolio import _Interactive, Account, logger, make_parser, Portfolio, Report


def main() -> None:
    """Use parsed command line and config file options to produce a formatted report."""
    config = ConfigParser()
    portfolio_configs = ["portfolio.ini", join(str(Path.home()), "portfolio.ini")]
    logger.debug("Reading configuration from %s...", portfolio_configs)
    config.read(portfolio_configs)
    with Portfolio() as portfolio:
        args = make_parser().parse_args()
        if hasattr(args, "func"):
            args = args.func(args, portfolio, config)
        # report = Report(portfolio, config=config)
        # if args.email:
        # report.email(args.test)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.debug("Exiting...")
