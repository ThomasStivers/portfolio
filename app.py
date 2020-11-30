from os.path import splitext

import pandas as pd

from cli import make_parser
from interactive import _Interactive
from portfolio import Portfolio
from report import Report


def main() -> None:
    """Use parsed command line options to produce a formatted report."""
    text_message = str()
    with Portfolio() as portfolio:
        report = Report(portfolio)
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
        if args.export_file:
            portfolio.export(args.export_file)
        if args.verbose and "row" in locals():
            print(row)
        portfolio.path = args.file
        if args.verbose:
            print(report.text)
        if args.output_file:
            if splitext(args.output_file.name)[1] == ".txt":
                args.output_file.write(report.text)
            if splitext(args.output_file.name)[1] == ".html":
                args.output_file.write(report.html)
            args.output_file.close()
        if args.email:
            report.email(args.test)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled")
