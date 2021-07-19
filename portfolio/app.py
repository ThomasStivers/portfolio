from pathlib import Path
import sys

from portfolio.config import PortfolioConfig
from portfolio.log import logger
from portfolio.portfolio import Portfolio
from portfolio.cli import make_parser


def main() -> None:
    """Entry point for the portfolio app."""
    logger.debug('Running "%s" in "%s"', " ".join(sys.argv), Path(".").resolve())
    with Portfolio() as portfolio:
        args = make_parser().parse_args()
        logger.debug("Arguments parsed as %s", args)
        if hasattr(args, "func"):
            with PortfolioConfig() as config:
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
