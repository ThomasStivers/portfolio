import argparse

import pandas as pd


def make_parser() -> argparse.ArgumentParser:
    """Parse the command line arguments determining what type of report to produce.

    :return: An `argparse.ArgumentParser` with all arguments added.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-a",
        "--all",
        dest="symbol",
        action="store_const",
        const="all",
        help="View a report for all holdings.",
    )
    parser.add_argument(
        "-c",
        "--cash",
        action="store_true",
        help="If specified the quantity for the  --add or --remove options will be specified as cash otherwise defaults to shares.",
    )
    parser.add_argument(
        "-d", "--date", default=pd.Timestamp.now(), help="The date to look up."
    )
    parser.add_argument(
        "-e", "--email", action="store_true", help="Email the portfolio report."
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactively make changes to the portfolio.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="Displays a list of the symbols available in the portfolio.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        type=argparse.FileType("w"),
        help="Write the report to a .html or .txt file. The format written depends on the file extension given.",
    )
    parser.add_argument(
        "-s", "--symbol", nargs="+", help="The stock ticker symbol(s) to look up."
    )
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="Used to test emails without sending.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Provide more detailed information.",
    )
    parser.add_argument(
        "-x",
        "--export",
        dest="export_file",
        help="Export holdings to a csv or xlsx file. The format of the output depends on the file extension",
    )
    parser.add_argument(
        "-A",
        "--add",
        nargs=3,
        metavar=("SYMBOL", "SHARES", "DATE"),
        help="Add shares of a given symbol for a given date.",
    )
    parser.add_argument(
        "-C",
        "--create",
        help="Create a new portfolio.",
    )
    parser.add_argument(
        "-F",
        "--file",
        default="holdings.h5",
        help=(
            "Name of the file where holdings and market data are stored. "
            "The default is %(default)s."
        ),
    )
    parser.add_argument(
        "-R",
        "--remove",
        nargs=3,
        metavar=("SYMBOL", "SHARES", "DATE"),
        help="Remove shares of a given symbol for a given date.",
    )
    parser.add_argument(
        "-S",
        "--set",
        nargs=3,
        metavar=("SYMBOL", "SHARES", "DATE"),
        help="Set count of shares of a given symbol for a given date.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Only use sample data in the portfolio.",
    )
    return parser
