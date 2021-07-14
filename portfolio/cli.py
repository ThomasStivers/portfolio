import argparse
from os.path import splitext

import pandas as pd  # type: ignore

from portfolio.interactive import _Interactive
from portfolio.log import logger
from portfolio.report import Report


def make_parser() -> argparse.ArgumentParser:
    """Parse the command line arguments determining what type of report to produce.

    :return: An `argparse.ArgumentParser` with all arguments added.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(title="Actions")
    # parser.add_argument(
    # "-q",
    # "--quiet",
    # action="count",
    # dest="verbosity",
    # help="Produce less output.",
    # )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help="Provide more detailed information.",
    )
    parser.add_argument(
        "-C",
        "--create",
        help="Create a new portfolio.",
    )
    parser.add_argument(
        "-F",
        "--folder",
        default="data",
        help=(
            "Name of the folder where holdings and market data are stored. "
            "The default is %(default)s."
        ),
    )
    # parser.add_argument(
    # "--sample",
    # action="store_true",
    # help="Only use sample data in the portfolio.",
    # )
    parser.set_defaults(func=report)
    interactive_parser = subparsers.add_parser(
        "interactive", help="Interactively make changes to the portfolio."
    )
    interactive_parser.set_defaults(func=interactive)
    list_parser = subparsers.add_parser("list", help="List the funds in the portfolio.")
    list_parser.set_defaults(func=list)
    report_parser = subparsers.add_parser(
        "report", help="Generate reports on accounts and portfolios."
    )
    report_parser.add_argument(
        "-a",
        "--all",
        dest="symbol",
        action="store_const",
        const="all",
        help="View a report for all holdings.",
    )
    report_parser.add_argument(
        "-d", "--date", default=pd.Timestamp.now(), help="The date to look up."
    )
    report_parser.add_argument(
        "-e",
        "--email",
        action="store_true",
        default=False,
        help="Email the portfolio report.",
    )
    report_parser.add_argument(
        "-o",
        "--output",
        default=None,
        dest="output_file",
        type=argparse.FileType("w"),
        help="Write the report to a .html or .txt file. The format written depends on the file extension given.",
    )
    report_parser.add_argument(
        "-s", "--symbol", nargs="+", help="The stock ticker symbol(s) to look up."
    )
    report_parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        default=False,
        help="Used to test emails without sending.",
    )
    report_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=1,
        help="Provide more detailed information.",
    )
    report_parser.add_argument(
        "-x",
        "--export",
        dest="export_file",
        type=argparse.FileType("w"),
        help="Export holdings to a csv or xlsx file. The format of the output depends on the file extension",
    )
    report_parser.set_defaults(func=report, email=False)
    update_parser = subparsers.add_parser(
        "update", help="Update accounts or portfolios."
    )
    update_parser.add_argument(
        "-A",
        "--add",
        nargs=3,
        metavar=("SYMBOL", "SHARES", "DATE"),
        help="Add shares of a given symbol for a given date.",
    )
    update_parser.add_argument(
        "-c",
        "--cash",
        action="store_true",
        help="The quantity for the  --add or --remove options will be specified as cash otherwise defaults to shares.",
    )
    update_parser.add_argument(
        "-R",
        "--remove",
        nargs=3,
        metavar=("SYMBOL", "SHARES", "DATE"),
        help="Remove shares of a given symbol for a given date.",
    )
    update_parser.add_argument(
        "-S",
        "--set",
        nargs=3,
        metavar=("SYMBOL", "SHARES", "DATE"),
        help="Set count of shares of a given symbol for a given date.",
    )
    update_parser.set_defaults(func=update)
    return parser


def interactive(args, portfolio, config):
    logger.debug("Running in interactive mode...")
    _Interactive(portfolio, args)
    return args


def list(args, portfolio, config=None):
    logger.debug("Listing holdings...")
    if args.verbosity < 1:
        listing = "\t".join(portfolio.holdings.columns)
    elif args.verbosity == 1:
        listing = portfolio.holdings.iloc[-1]
    else:
        listing = pd.DataFrame(
            index=portfolio.holdings.columns,
            columns=["Holdings", "Price", "Value"],
            data={
                "Holdings": portfolio.holdings.iloc[-1],
                "Price": portfolio.data.iloc[-1],
                "Value": portfolio.value.drop(columns="Total").iloc[-1],
            },
        )
    print(listing)
    return listing


def report(args, portfolio, config):
    logger.debug("Running report...")
    report = Report(portfolio, config=config, date=args.date)
    if hasattr(args, "email") and args.email:
        logger.debug("Emailing report...")
        report.email(args.test)
    if args.verbosity > 0:
        print(report.text)
    if args.output_file:
        logger.debug("Writing report to %s...", args.output_file.name)
        if splitext(args.output_file.name)[1] == ".txt":
            args.output_file.write(report.text)
        if splitext(args.output_file.name)[1] == ".html":
            args.output_file.write(report.html)
        args.output_file.close()
    if args.export_file:
        portfolio.export(args.export_file.name)
    # return report


def update(args, portfolio, config):
    logger.debug("Updating portfolio...")
    if args.add:
        args.add[1] = float(args.add[1])
        args.add[2] = pd.Timestamp(args.add[2])
        if args.cash:
            row = portfolio.add_cash(*args.add)
        else:
            row = portfolio.add_shares(*args.add)
    elif args.remove:
        args.remove[1] = float(args.remove[1])
        args.remove[2] = pd.Timestamp(args.remove[2])
        if args.cash:
            row = portfolio.remove_cash(*args.remove)
        else:
            row = portfolio.remove_shares(*args.remove)
    elif args.set:
        args.set[1] = float(args.set[1])
        args.set[2] = pd.Timestamp(args.set[2])
        row = portfolio.set_shares(*args.set)
    logger.debug("Portfolio updated with %s.", row)
    return args
