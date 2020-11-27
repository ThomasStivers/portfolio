from textwrap import fill

import pandas as pd

from interactive import _Interactive
from portfolio import Portfolio
from cli import make_parser


def main() -> None:
    """Use parsed command line options to produce a formatted report."""
    text_message = str()
    with Portfolio() as portfolio:
        args = make_parser().parse_args()
        if args.interactive:
            _Interactive(portfolio, args)
        elif args.add:
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
        elif args.date:
            args.date = pd.Timestamp(args.date)
        elif args.list:
            text_message += "\t".join(portfolio.holdings.columns)
        if args.export:
            portfolio.export(args.export)
        if args.verbose and "row" in locals():
            print(row)
        portfolio.path = args.file
        if args.verbose:
            text_message = portfolio.report(args)["text"]
            text_message = "\n".join(
                [fill(txt, 120) for txt in text_message.split("\n")]
            )
            print(text_message)
        if args.email:
            portfolio.email(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled")
