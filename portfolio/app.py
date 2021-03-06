from configparser import ConfigParser
from os.path import join, splitext
from pathlib import Path
import sys

from portfolio import logger, make_parser, Portfolio


def main() -> None:
    """Entry point for the portfolio app."""
    logger.debug('Running "%s" in "%s"', " ".join(sys.argv), Path(".").resolve())
    config = ConfigParser()
    portfolio_configs = ["portfolio.ini", join(str(Path.home()), "portfolio.ini")]
    logger.debug("Reading configuration from %s...", portfolio_configs)
    config.read(portfolio_configs)
    with Portfolio() as portfolio:
        args = make_parser().parse_args()
        logger.debug("Arguments parsed as %s", args)
        if hasattr(args, "func"):
            args.func(args, portfolio, config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.debug("Exiting by keyboard interrupt...")
    except Exception:
        logger.exception("Fatal error in main.")
        raise
    logger.debug("%s exited.", __name__)
