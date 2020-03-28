#!/usr/bin/python3
"""Portfolio Management Tool

Examples:
    >>> import portfolio
    
    Create a portfolio from test data and holdings.
    
    >>> pf = portfolio.Portfolio(None, portfolio.test_data(), portfolio.test_holdings())
    >>> print(pf) # doctest: +ELLIPSIS
    Portfolio holding ... instruments for ... dates worth $...
    >>> sys.argv = ["", "--all", "--verbose"]
    >>> args = pf.parse_args()
    >>> print(pf.report(args)["text"]) # doctest: +ELLIPSIS
    # ... Portfolio Report for January 07, 2020 #
    Total holdings were **$....** This is ... of $... or ...% from the previous day. The annual ranking[^1] is ... out of ...
    ## Individual Holdings Reports ##
    *   Total holdings of TEST were **$....** This is ... of ($...) or ...% from the previous day. The annual ranking is ... out of ...  for TEST.
    *   Total holdings of SAMPLE were **$....** This is ... of $... or ...% from the previous day. The annual rank ing is ... out of ...  for SAMPLE.
    <BLANKLINE>
    |        |       01/01 |    01/02 |       01/03 |       01/06 |    01/07 |
    |:-------|------------:|---------:|------------:|------------:|---------:|
    | TEST   | ...    | ... | ...    | ...    | ... |
    | SAMPLE | ...    | ... | ...    | ...    | ... |
    | Total  | ...    | ... | ...    | ...    | ... |
    <BLANKLINE>
    [^1]: Rankings are based on the cash value of the change in the portfolio on a given date with 1 being the best day of the year.
    <BLANKLINE>
    

"""
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
import smtplib
import sys

# Use BeautifulSoup to get plain text version of the report.
from bs4 import BeautifulSoup

# The markdown module is used for html email reports.
from markdown import Markdown

# Imports for pandas and related modules
import pandas as pd
import numpy as np
from pandas_datareader import DataReader

# Pandas options
pd.set_option("display.float_format", "{:,.2f}".format)
pd.set_option("colheader_justify", "center")


def test_data() -> pd.DataFrame:
    """Generate sambple data."""
    data = pd.DataFrame(
        data=10 * np.random.randn(5, 12) + 100,
        index=pd.date_range("2020-01-01", periods=5, freq="b"),
        columns=pd.MultiIndex.from_product(
            iterables=[
                ["Adj Close", "Close", "High", "Low", "Open", "Volume"],
                ["TEST", "SAMPLE"],
            ],
            names=["Attributes", "Symbols"],
        ),
    )
    return data


def test_holdings() -> pd.DataFrame:
    """Generate sample holdings."""
    holdings = pd.DataFrame(
        data=np.random.randn(5, 2) + 10,
        index=pd.date_range("2020-01-01", periods=5, freq="b"),
        columns=["TEST", "SAMPLE"],
    )
    return holdings


class Portfolio(object):
    """Provides information about a portfolio of financial instruments."""

    def __init__(
        self,
        path: str = "holdings.h5",
        data: pd.DataFrame = None,
        holdings: pd.DataFrame = None,
    ):
        """Initialize the portfolio with holdings and market data.
        
        Args:
            path: The name of an hdf file containing holdings and market data. If this
                is None then the portfolio must be described by the data and holdings arguments.
            data: A DataFrame with multiple indices containing market data for a set of
                financial instruments over a period of time.
                The level 0 index is Adj Close, Close, High, Low, Open, and Volume.
                The level 1 index has one item for each ticker symbol being tracked.
            holdings:   A DataFrame containing the number of shares held of the set of
                symbols in data over a time period corresponding to that of data.
        
        Examples:
            >>> pf = Portfolio(
            ...     path=None,
            ...     data=test_data(),
            ...     holdings=test_holdings(),
            ... )
            >>> pf.data.shape
            (5, 12)
            >>> pf.holdings.shape
            (5, 2)
        
        """
        today = pd.Timestamp.floor(pd.Timestamp.today(), "D")
        yesterday = today - pd.Timedelta("1D")
        ytd_range = pd.date_range(pd.Timestamp(today.year, 1, 1), today, freq="B")
        if path:
            self.path = Path(path)
        if type(data) == pd.DataFrame and type(holdings) == pd.DataFrame:
            self.data = data
            self.holdings = holdings
        elif path and self.path.is_file():
            with pd.HDFStore(self.path, "r") as store:
                self.holdings = store["/holdings"]
                try:
                    self.data = store["/data"]
                except (KeyError):
                    self.data = DataReader(
                        self.holdings.columns,
                        "yahoo",
                        pd.Timestamp(today.year - 1, 12, 31),
                    )
        # if we don't have given data, and it is a day we don't have data for, and it is
        # after market close.
        if (
            type(data) != pd.DataFrame
            and self.data.index.max() < yesterday
            and yesterday.dayofweek in range(0, 5)
            or pd.Timestamp.now() > pd.Timestamp("16:00")
        ):
            self.data = DataReader(
                self.holdings.columns, "yahoo", pd.Timestamp(today.year - 1, 12, 31)
            )
        self.holdings = self.holdings.reindex(self.data.index, method="ffill")

    @property
    def value(self) -> pd.DataFrame:
        """The value of the held shares at closing on each date.
        
        Returns:
            The market closing price of all instruments multiplied by the number of held
            shares for all dates.
            
        """
        value = self.data["Close"] * self.holdings.fillna(method="bfill")
        return value

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """Stores market and holdings data to an HDF file.
        
        Examples:
            >>> with Portfolio() as pf: pass
        
        """
        self.holdings.to_hdf(self.path, key="/holdings")
        self.data.to_hdf(self.path, key="/data")

    def __str__(self) -> str:
        """Briefly describe the holdings in the portfolio in a string.
        
        Returns:
            A string briefly summarizing the contents of the portfolio.
            
            Examples:
                >>> print(Portfolio(data=test_data(), holdings=test_holdings())) # doctest: +ELLIPSIS
                Portfolio holding ... instruments for ... dates worth $...
                
        """
        return (
            f"Portfolio holding {self.holdings.shape[1]} instruments "
            f"for {self.holdings.shape[0]} dates "
            f"worth ${self.value.iloc[-1].sum():,.2f}."
        )

    def add_shares(
        self, symbol: str, quantity: float, date: pd.Timestamp, testing: bool = True
    ) -> pd.Series:
        """Add shares of an instrument to holdings on given date.
        
        Args:
            symbol: A stock ticker symbol.
            quantity: The number of shares to be added.
            date: The date on which the shares should be added to the portfolio.
            testing: If true the addition will not be saved in the portfolio, but the
                share price will be calculated. If false then the addition will be made.
            
        Returns:
            The holdings on the given date with the addition included.
        
        Examples:
            >>> output = Portfolio().add_shares('FIPDX', 100, '2020-01-02', testing=True)
            1655.246
            >>> output['FIPDX'] == 1555.246
            True
        
        
        """
        if symbol not in self.holdings.columns:
            raise IndexError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        if not testing:
            self.holdings.loc[date, symbol] += quantity
        else:
            print(self.holdings.loc[date, symbol] + quantity)
        return self.holdings.loc[date]

    def add_symbol(self, symbol: str, quantity: loat, date: pd.Timestamp) -> None:
        """Add a new symbol to the portfolio."""
        if symbol in self.holdings.columns:
            raise KeyError(
                f"symbol is already inportfolio. Use add_shares or add_cash instead."
            )
            self.holdings.loc[date, symbol] = quantity

    def remove_shares(
        self, symbol: str, quantity: float, date: pd.Timestamp, testing: bool = True
    ) -> pd.Series:
        """Remove shares of an instrument from holdings on given date.
        
        Args:
            symbol: A stock ticker symbol.
            quantity: The number of shares to be removed.
            date: The date on which the shares should be removed from the portfolio.
            testing: If true the removal will not be saved in the portfolio, but the share price will be calculated. If false then the removal will be made.
            
        Returns:
            The holdings on the given date with the removal included.
            
        """
        if symbol not in self.holdings.columns:
            raise IndexError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        if not testing:
            self.holdings.loc[date, symbol] -= quantity
        print(self.holdings[symbol].tail())
        return self.holdings.loc[date]

    def add_cash(
        self, symbol: str, quantity: float, date: pd.Timestamp, testing: bool = True
    ) -> pd.Series:
        """Add shares purchasable by given quantity of cash of an instrument to holdings on given date.        
        
        Args:
            symbol: A stock ticker symbol.
            quantity: The number of dollars to be added.
            date: The date on which the dollars should be added to the portfolio.
            testing: If true the addition will not be saved in the portfolio, but the share price will be calculated. If false then the addition will be made.
            
        Returns:
            The holdings on the given date with the addition included.
        
        Examples:
            >>> Portfolio().add_shares('ERROR', 100, pd.Timestamp('2020-01-01'), testing=False)
            Traceback (most recent call last):
                ...
            IndexError: symbol must be in holdings.
            >>> Portfolio().add_shares('FSKAX', -100, pd.Timestamp('2020-01-01'), testing=True)
            Traceback (most recent call last):
                ...
            ValueError: quantity must be > 0.
            
        """
        if symbol not in self.holdings.columns:
            raise IndexError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        shares = self.to_shares(symbol, quantity, date)
        if not testing:
            self.holdings.loc[date, symbol] += shares
        print(self.holdings[symbol].tail())
        return self.holdings.loc[date]

    def remove_cash(
        self, symbol: str, quantity: float, date: pd.Timestamp, testing: bool = True
    ) -> pd.Series:
        """Remove shares purchasable by given quantity of cash of an instrument from holdings on given date.        
        
        Args:
            symbol: A stock ticker symbol.
            quantity: The number of dollars to be removed.
            date: The date on which the dollars should be removed from the portfolio.
            testing: If true the removal will not be saved in the portfolio, but the share price will be calculated. If false then the removal will be made.
            
        Returns:
            The holdings on the given date with the removal included.
            
        """
        shares = self.to_shares(symbol, quantity, date)
        if not testing:
            self.holdings.loc[date, symbol] -= shares
        print(self.holdings[symbol].tail())
        return self.holdings.loc[date]

    def to_cash(self, symbol: str, shares: float, date: pd.Timestamp) -> float:
        """Get the cash value  of a given number of shares of an instrument  on a given date.
        
        Args:
            symbol: The ticker symbol to get the cash value.
            shares: The number of shares to get the cash value for.
            date: The date whose closing price should be used.
        
        Returns:
            The value of the shares of symbol in dollars on the specified date.
            
        """
        last_close = self.data["Close"].iloc[
            self.data["Close"].index.get_loc(date, method="ffill")
        ][symbol]
        cash = shares * last_close
        print(f"${cash:,.2f} = {shares:,.3f} shares of {symbol}")
        return cash

    def to_shares(self, symbol: str, cash: float, date: pd.Timestamp) -> float:
        """Get the number of shares of an instrument purchasable for a given price on a given date.        
        
        Args:
            symbol: The ticker symbol to get the share count.
            cash: The number of dollars to get the share count for.
            date: The date whose closing price should be used.
        
        Returns:
            The count of  shares of symbol purchasable for cash on the specified date.
            
        """
        last_close = self.data["Close"].iloc[
            self.data["Close"].index.get_loc(date, method="ffill")
        ][symbol]
        shares = cash / last_close
        print(f"${cash:,.2f} = {shares:,.3f} shares of {symbol}")
        return shares

    def export(self) -> None:
        """Export the holdings in the portfolio to a csv file."""
        self.holdings.drop_duplicates().to_csv("holdings.csv")

    def report(self, args: argparse.Namespace) -> dict:
        """Produce a dictionary of two report strings in text and html.
        
        Args:
            args: The arguments given on the command line and parsed by Portfolio.parse_args().
        
        Returns:
            A dictionary with two keys "text" and "html" which contain the same report in those formats.
        
        """
        markdown = Markdown(extensions=["footnotes", "tables"])
        report = {"text": "", "html": ""}
        charts = {"up": "&#X1F4C8;", "down": "&#X1F4C9;"}
        colors = [
            "#003f5c",
            "#374c80",
            "#7a5195",
            "#bc5090",
            "#ef5675",
            "#ff764a",
            "#ffa600",
        ]
        symbol_colors = dict(zip(self.holdings.columns, colors))
        footnotes = (
            "[^1]: Rankings are based on the cash value of the change in the portfolio "
            "on a given date with 1 being the best day of the year.\n"
        )
        date_string = pd.Timestamp(args.date).strftime("%B %d, %Y")
        value = self.value.loc[args.date].sum()
        daily_totals = self.value.sum(axis=1)
        difference = daily_totals.diff()[args.date]
        if difference < 0:
            difference_string = (
                f'a decrease of <span class="decrease">(${abs(difference):,.2f})</span>'
            )
        else:
            difference_string = (
                f'an increase of <span class="increase">${difference:,.2f}</span>'
            )
        pct_difference = daily_totals.pct_change(1)[args.date] * 100
        ranking = daily_totals.diff().rank(ascending=False)[args.date]
        if args.date in pd.date_range(args.date, freq="bm", periods=1):
            report["text"] += self.periodic_report(args, "28d")
        if args.date.dayofweek == 4:
            report["text"] += self.periodic_report(args, "7d")
        report["text"] += (
            f"# {charts['up'] if difference > 0 else charts['down']} "
            f"Portfolio Report for {date_string} #\n"
            f"Total holdings were **${value:,.2f}.** "
            f"This is {difference_string} "
            f"or {abs(pct_difference):.2f}% from the previous day. "
            f"The annual ranking[^1] is {ranking:.0f} out of {len(self.value) - 1}.\n"
        )
        if args.symbol:
            report["text"] += f"## Individual Holdings Reports ##\n"
            for symbol in args.symbol:
                value = self.value.loc[args.date, symbol]
                difference = self.value[symbol].diff()[args.date]
                if difference < 0:
                    difference_string = (
                        "a decrease of "
                        f'<span class="decrease">(${abs(difference):,.2f})</span>'
                    )
                else:
                    difference_string = (
                        "an increase of "
                        f'<span class="increase">${difference:,.2f}</span>'
                    )
                pct_difference = self.value[symbol].pct_change(1)[args.date] * 100
                ranking = self.value[symbol].diff().rank(ascending=False)[args.date]
                colored_symbol = (
                    f'<span style="color: {symbol_colors[symbol]}">{symbol}</span>'
                )
                report["text"] += (
                    f"*   Total holdings of {colored_symbol} were **${value:,.2f}.** "
                    f"This is {difference_string} "
                    f"or {abs(pct_difference):.2f}% from the previous day. "
                    f"The annual ranking is {ranking:.0f} "
                    f"out of {len(self.value) - 1}  for {colored_symbol}.\n"
                )
            table_range = self.value.index[
                self.value.index.get_loc(args.date)
                - 4 : self.value.index.get_loc(args.date)
                + 6
            ]
            table_data = self.value.loc[table_range, args.symbol]
            table_data["Total"] = table_data.sum(axis=1)
            table_data = table_data.T
            table_headers = table_range.strftime("%m/%d")
            table_data.columns = table_headers
            table_html = table_data.to_html(
                float_format="${:,.2f}".format, classes="symbol_table"
            )
            report["text"] = BeautifulSoup(report["text"], features="lxml").get_text()
            report["text"] += "\n"
            report["text"] += table_data.to_markdown(
                floatfmt=",.2f", headers=table_headers
            )
        report["text"] += "\n\n"
        report["text"] += footnotes
        symbol_table_row_styles = "\n".join(
            [
                f"tbody tr:nth-child({row+1}) {{ color: {color}; }}"
                for row, color in enumerate(colors)
            ]
        )
        soup = BeautifulSoup(
            (
                "<html>\n"
                "<head>\n"
                "<title>Portfolio Report</title>\n"
                "<style>\n"
                "body {\n"
                'font-family: "Arial";\n'
                'font-size: "12pt";\n'
                "}\n"
                "strong {\n"
                'font-weight: "normal";\n'
                "text-decoration-line: underline;\n"
                "text-decoration-style: double;\n"
                "}\n"
                ".decrease {\n"
                "color: red;\n"
                "}\n"
                f"{symbol_table_row_styles}\n"
                "</style>\n"
                "</head>\n"
                "<body>\n"
                f"{markdown.convert(report['text'])}\n"
                "</body>\n"
                "</html>\n"
            ),
            features="lxml",
        )
        soup.table.replace_with(BeautifulSoup(table_html, features="lxml").table)
        report["html"] = soup.prettify()
        return report

    def periodic_report(
        self, args: argparse.Namespace, period: pd.offsets.DateOffset = "7d"
    ) -> str:
        """Produce a text string for a given period to be included in the larger portfolio report."""
        report = "# {period} Report for {start} through {end} #\n"
        days = pd.date_range(args.date - pd.Timedelta(period), args.date)
        report = report.format(
            period=("Weekly" if period == "7d" else "Monthly"),
            start=days[0].strftime("%m/%d"),
            end=days[-1].strftime("%m/%d"),
        )
        value = self.value.loc[days[0] : days[-1]].sum(axis=1)
        difference = value.diff().sum()
        pct_difference = value.pct_change(1).sum() * 100
        if difference < 0:
            difference_string = (
                f'a decrease of <span class="decrease">(${abs(difference):,.2f})</span>'
            )
        else:
            difference_string = (
                f'an increase of <span class="increase">${difference:,.2f}</span>'
            )
        report += (
            f"Holdings have had {difference_string} or {abs(pct_difference):.2f}% "
            f"from the previous period.\n"
            "## Changes in shares held ##\n"
        )
        share_changes = (
            self.holdings[days[0] : days[-1]].drop_duplicates().diff().dropna()
        )
        if share_changes.any().any():
            changes = []
            for symbol, change in share_changes.items():
                changes += [
                    (
                        f"*   Holdings of {symbol} changed by {shares:,.3f} shares "
                        f"valued at ${self.data.Close.loc[date, symbol] * shares:,.2f} "
                        f"on {date.strftime('%m/%d')}."
                    )
                    for date, shares in change.items()
                    if shares > 0
                ]
            report += "".join(changes)
        return report

    def email(self, args: argparse.Namespace = None) -> str:
        """Send the portfolio report by email."""
        sender = "Thomas Stivers <thomas.stivers+portfolio@gmail.com>"
        recipients = [
            "Thomas Stivers <thomas.stivers@gmail.com>",
            "Heather Stivers <heather.stivers@gmail.com>",
        ]
        message = MIMEMultipart("alternative")
        message["From"] = sender
        message["Reply-To"] = "thomas.stivers@gmail.com"
        message["To"] = ", ".join(recipients)
        message["Message-ID"] = make_msgid(domain="gmail.com")
        message["Date"] = formatdate(localtime=True)
        message["Subject"] = "Portfolio Report"
        report = self.report(args)
        with open("message.html", "w", encoding="utf-8") as file:
            file.write(report["html"])
        part1 = MIMEText(report["text"], "plain", "utf-8")
        part2 = MIMEText(report["html"], "html")
        message.attach(part1)
        message.attach(part2)
        if args.test:
            print(message.as_string())
            return
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("thomas.stivers@gmail.com", "cwtlgzcpaoxhmlib")
            smtp.send_message(message)

    def parse_args(self) -> argparse.Namespace:
        """Parse the command line arguments determining what type of report to produce.
        
        Returns:
            The parsed argument list from the command line.
        
        Tests:
            >>> pf=Portfolio(data=test_data(), holdings=test_holdings())
            >>> pf.parse_args()
        
        """
        parser = argparse.ArgumentParser(description=self.__doc__)
        parser.add_argument(
            "-a",
            "--all",
            dest="symbol",
            action="store_const",
            const=list(self.holdings.columns),
            help="View a report for all holdings.",
        )
        parser.add_argument(
            "-c",
            "--cash",
            action="store_true",
            help="If specified the quantity for the  --add or --remove options will be specified as cash otherwise defaults to shares.",
        )
        parser.add_argument(
            "-d", "--date", default=self.data.index.max(), help="The date to look up."
        )
        parser.add_argument(
            "-e", "--email", action="store_true", help="Email the portfolio report."
        )
        parser.add_argument(
            "-l",
            "--list",
            action="store_true",
            help="Displays a list of the symbols available in the portfolio.",
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
            action="store_true",
            help="Export holdings to a csv file.",
        )
        parser.add_argument(
            "-A",
            "--add",
            nargs=3,
            metavar=("SYMBOL", "SHARES", "DATE"),
            help="Add shares of a given symbol for a given date.",
        )
        parser.add_argument(
            "-F",
            "--file",
            default="holdings.h5",
            help=(
                "Name of the file where holdings and market data are stored. "
                "The default is %(default)s.",
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
            "--sample",
            action="store_true",
            help="Only use sample data in the portfolio.",
        )
        parser.add_argument(
            "--save",
            action="store_true",
            help="Save changes made with --add or --remove options permanently.",
        )
        return parser.parse_args()


def main():
    """Use parsed command line options to produce a formatted report."""
    text_message = str()
    with Portfolio() as portfolio:
        args = portfolio.parse_args()
        testing = not args.save
        if args.add:
            args.add[1] = float(args.add[1])
            args.add[2] = pd.Timestamp(args.add[2])
            if args.cash:
                row = portfolio.add_cash(*args.add, testing)
            else:
                row = portfolio.add_shares(*args.add, testing)
        elif args.remove:
            args.remove[1] = float(args.remove[1])
            args.remove[2] = pd.Timestamp(args.remove[2])
            if args.cash:
                row = portfolio.remove_cash(*args.remove, testing)
            else:
                row = portfolio.remove_shares(*args.remove, testing)
        elif args.date:
            args.date = pd.Timestamp(args.date)
        elif args.list:
            text_message += "\t".join(portfolio.holdings.columns)
        elif args.export:
            portfolio.export()
        if args.verbose and "row" in locals():
            print(row)
        portfolio.path = args.file
        if args.verbose:
            text_message = portfolio.report(args)["text"]
            print(text_message, end="")
        if args.email:
            portfolio.email(args)


if __name__ == "__main__":
    main()
