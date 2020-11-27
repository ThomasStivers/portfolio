#!/usr/bin/python3
"""A tool for managing a stock portfolio."""
import argparse
import configparser
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import os
from pathlib import Path
import smtplib
import sys
import tempfile

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
    """Generate sambple data.

    :returns: A `DataFrame` containing 5 days worth of random values for 2 sample symbols.

    """
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
    """Provides information about a portfolio of financial instruments.

    Examples:
        >>> import portfolio

        Create a portfolio from test data and holdings.

        >>> pf = portfolio.Portfolio(None, portfolio.test_data(), portfolio.test_holdings())
        >>> print(pf) # doctest: +ELLIPSIS
        Portfolio holding ... instruments for ... dates worth $...
        >>> sys.argv = ["", "--all", "--verbose"]
        >>> args = make_parser(sys.argv).parse_args()
        >>> print(pf.report(args)["text"]) # doctest: +ELLIPSIS
        # ... Portfolio Report for January 07, 2020 #
        Total holdings were **$....** This is ... of $... or ...% from the previous day. The annual ranking[^1] is ... out of ...
        ## Individual Holdings Reports ##
        *   Total holdings of TEST were **$.    ...** This is ... of ($...) or ...% from the previous day. The annual ranking is ... out of ...  for TEST.
        *   Total holdings of SAMPLE were **$....** This is ... of $... or ...% from the previous day. The annual rank ing is ... out of ...  for SAMPLE.
        <BLANKLINE>
        |        |           01/01 |    01/02 |       01/03 |       01/06 |    01/07 |
        |:-------|------    ------:|---------:|------------:|------------:|---------:|
        | TEST   | ...    |     ... | ...    | ...    | ... |
        | SAMPLE | ...    | ...     | ...    | ...    | ... |
        | Total  | ...    | ... | ..    .    | ...    | ... |

    """

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
        self.config = configparser.ConfigParser()
        self.config_name = "portfolio.ini"
        self.config.read(
            [self.config_name, os.path.join(str(Path.home()), self.config_name)]
        )
        today = pd.Timestamp.floor(pd.Timestamp.today(), "D")
        yesterday = today - pd.Timedelta("1D")
        if type(data) == pd.DataFrame and type(holdings) == pd.DataFrame:
            self.data = data
            self.holdings = holdings
        if path:
            self.path = Path(path)
            if not self.path.is_file():
                self.path.touch()
        if self.path.is_file():
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
                self.holdings.columns, "yahoo", pd.Timestamp(today.year, 1, 1)
            )
        self.holdings = self.holdings.reindex(self.data.index, method="ffill").dropna()

    @property
    def value(self) -> pd.DataFrame:
        """The value of the held shares at closing on each date.

        Returns:
            The market closing price of all instruments multiplied by the number of held
            shares for all dates. Includes a Totals column with the value of all shares held on a given date.

        """
        value = self.data["Close"] * self.holdings.fillna(method="bfill")
        value["Total"] = value.sum(axis=1)
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

    def add_shares(self, symbol: str, quantity: float, date: pd.Timestamp) -> pd.Series:
        """Add shares of an instrument to holdings on given date.

        :param symbol: A stock ticker symbol.
        :param quantity: The number of shares to be added.
        :param date: The date on which the shares should be added to the portfolio.

        :return: The holdings on the given date with the addition included.

        :Examples:
            >>> output = Portfolio().add_shares('FIPDX', 100, '2020-01-02')
            1655.246
            >>> output['FIPDX'] == 1555.246
            True


        """
        if symbol not in self.holdings.columns:
            raise KeyError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        self.holdings.loc[date:, symbol] += quantity
        return self.holdings.loc[date]

    def add_symbol(self, symbol: str, quantity: float, date: pd.Timestamp) -> None:
        """Add a new symbol to the portfolio.

        :param symbol: A ticker symbol.
        :param quantity: Initial quantity of shares of symbol.
        :param date: The shares must be added on a date.

        :raises KeyError: The symbol is already in the portfolio.
        """
        if symbol in self.holdings.columns:
            raise KeyError(
                f"symbol is already inportfolio. Use add_shares or add_cash instead."
            )
            self.holdings.loc[date:, symbol] = quantity
            try:
                self.data.append(DataReader(symbol, "yahoo", self.data.idxmin()))
            except KeyError:
                pass

    def remove_shares(
        self, symbol: str, quantity: float, date: pd.Timestamp
    ) -> pd.Series:
        """Remove shares of an instrument from holdings on given date.

        Args:
            symbol: A stock ticker symbol.
            quantity: The number of shares to be removed.
            date: The date on which the shares should be removed from the portfolio.

        Returns:
            The holdings on the given date with the removal included.

        """
        if symbol not in self.holdings.columns:
            raise KeyError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        self.holdings.loc[date:, symbol] -= quantity
        return self.holdings.loc[date]

    def set_shares(self, symbol: str, quantity: float, date: pd.Timestamp) -> pd.Series:
        """Set the count of shares of an instrument to holdings on given date.

        :param symbol: A stock ticker symbol.
        :param quantity: The number of shares to be in holdings on and after date.
        :param date: The date on which the share count should be set on the portfolio.

        :return: The holdings on the given date set to quantity.

        :Examples:
            >>> output = Portfolio().set_shares('FIPDX', 100, '2020-01-02')
            100
            >>> output['FIPDX'] == 100
            True


        """
        if symbol not in self.holdings.columns:
            raise KeyError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        self.holdings.loc[date:, symbol] = quantity
        return self.holdings.loc[date]

    def add_cash(self, symbol: str, quantity: float, date: pd.Timestamp) -> pd.Series:
        """Add shares purchasable for  cash value of symbol to holdings on given date.

        :param symbol: A stock ticker symbol.
        :param quantity: The number of dollars to be added.
        :param date: The date on which the dollars should be added to the portfolio.

        :returns: The holdings on the given date with the addition included.
        """
        if symbol not in self.holdings.columns:
            raise KeyError("symbol must be in holdings.")
        if quantity <= 0:
            raise ValueError("quantity must be > 0.")
        shares = self.to_shares(symbol, quantity, date)
        self.holdings.loc[date:, symbol] += shares
        return self.holdings.loc[date]

    def remove_cash(
        self, symbol: str, quantity: float, date: pd.Timestamp
    ) -> pd.Series:
        """Remove shares purchasable by given quantity of cash of an instrument from holdings on given date.

        :param symbol: A stock ticker symbol.
        :param quantity: The number of dollars to be removed.
        :param date: The date on which the dollars should be removed from the portfolio.

        :returns: The holdings on the given date with the removal included.
        """
        shares = self.to_shares(symbol, quantity, date)
        self.holdings.loc[date:, symbol] -= shares
        return self.holdings.loc[date]

    def to_cash(self, symbol: str, shares: float, date: pd.Timestamp) -> float:
        """Get the cash value  of a given number of shares of an instrument  on a given date.

        :param symbol: The ticker symbol to get the cash value.
        :param shares: The number of shares to get the cash value for.
        :param date: The date whose closing price should be used.

        :returns: The value of the shares of symbol in dollars on the specified date.
        """
        prices = self.data[("Close", symbol)]
        date_index = prices.index.get_loc(date, method="ffill")
        date = prices.index[date_index]
        price = prices[date]
        cash = shares * price
        print(f"${cash:,.2f} = {shares:,.3f} shares of {symbol}")
        return cash

    def to_shares(self, symbol: str, cash: float, date: pd.Timestamp) -> float:
        """Get the number of shares of an instrument purchasable for a given price on a given date.

        :param symbol: The ticker symbol to get the share count.
        :param cash: The number of dollars to get the share count for.
        :param date: The date whose closing price should be used.

        :returns: The count of  shares of symbol purchasable for cash on the specified date.
        """
        last_close = self.data["Close"].iloc[
            self.data["Close"].index.get_loc(date, method="ffill")
        ][symbol]
        shares = cash / last_close
        print(f"${cash:,.2f} = {shares:,.3f} shares of {symbol}")
        return shares

    def export(self, filename: str = "holdings.csv") -> None:
        """Export the holdings in the portfolio to a file.

        :param filename: A CSV or XLSX file where holdings data should be exported.
        """
        if filename.endswith(".csv"):
            self.holdings.drop_duplicates().to_csv(filename)
        elif filename.endswith(".xlsx"):
            with pd.ExcelWriter(filename, datetime_format="mm/dd/yyyy") as writer:
                self.holdings.drop_duplicates().to_excel(writer, sheet_name="Holdings")
                self.value.to_excel(writer, sheet_name="Value")

    def report(self, args: argparse.Namespace) -> dict:
        """Produce a dictionary of two report strings in text and html.

        :param args: The arguments given on the command line and parsed by make_parser().parse_args().

        :returns: A dictionary with two keys "text" and "html" which contain the same report in those formats.
        """
        markdown = Markdown(extensions=["tables"])
        report = {"text": "", "html": ""}
        charts = {"up": "&#X1F4C8;", "down": "&#X1F4C9;"}
        args.date = self.data.index[self.data.index.get_loc(args.date, method="pad")]
        date_string = pd.Timestamp(args.date).strftime("%B %d, %Y")
        value = self.value.loc[args.date, "Total"]
        daily_totals = self.value["Total"].dropna()
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
        rank_change = daily_totals.diff().rank(ascending=False)[args.date]
        rank_value = daily_totals.rank(ascending=False)[args.date]
        if args.date in pd.date_range(args.date, freq="bm", periods=1):
            report["text"] += f"{self.periodic_report(args, '28d')}\n"
        if args.date.dayofweek == 4:
            report["text"] += f"{self.periodic_report(args, '7d')}\n"
        report["text"] += (
            f"# {charts['up'] if difference > 0 else charts['down']} "
            f"Portfolio Report for {date_string} #\n"
            f"Total holdings were **${value:,.2f}.** "
            f"This is {difference_string} "
            f"or {abs(pct_difference):.2f}% from the previous day. "
            f"The annual ranking for the changes on this day is {rank_change:.0f} "
            f"of {len(daily_totals)}. "
            f"and this portfolio balance is ranked {rank_value:.0f} "
            f"of {len(daily_totals)}.\n"
        )
        if args.symbol == "all":
            args.symbol = list(self.holdings.columns)
        if args.symbol:
            report["text"] += f"## Individual Holdings Reports ##\n"
            for symbol in args.symbol:
                if self.holdings.loc[args.date, symbol] <= 0:
                    continue
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
                rank_change = self.value[symbol].diff().rank(ascending=False)[args.date]
                rank_value = self.value[symbol].rank(ascending=False)[args.date]
                colored_symbol = f'<span style="color: {self.config[symbol]["color"]}">{symbol}</span>'
                report["text"] += (
                    f"*   {charts['up'] if difference > 0 else charts['down']} "
                    f"Total holdings of {colored_symbol} were **${value:,.2f}.** "
                    f"This is {difference_string} "
                    f"or {abs(pct_difference):.2f}% from the previous day. "
                    f"The annual ranking for the change in {colored_symbol} "
                    f"is {rank_change:.0f} "
                    f" of {len(self.value)} "
                    f"and the balance is ranked {rank_value:.0f} "
                    f"of {len(self.value)}.\n"
                )
            table_range = self.value.index[
                self.value.index.get_loc(args.date)
                - 4 : self.value.index.get_loc(args.date)
                + 6
            ]
            table_data = self.value.loc[table_range, args.symbol]
            # If we only have 0 values don't show the symbol.
            table_data = table_data.loc[:, (table_data != 0).any(axis=0)]
            table_data["Total"] = table_data.sum(axis=1)
            table_data = table_data.T
            table_headers = table_range.strftime("%b-%d")
            table_data.columns = table_headers
            table_html = table_data.to_html(
                float_format="${:,.2f}".format, classes="symbol_table"
            )
            report["html"] = report["text"]
            report["text"] = BeautifulSoup(report["text"], features="lxml").get_text()
            # Add a placeholder table which will be replaced with proper html.
            report["html"] += "\n<table/>"
            report["text"] += "\n"
            report["text"] += table_data.to_markdown(
                floatfmt=",.2f", headers=table_headers
            )
        symbol_table_row_styles = "\n".join(
            [
                f"tbody tr:nth-child({row+1}) {{ color: {self.config[symbol]['color']}; }}"
                for row, symbol in enumerate(self.holdings.columns)
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
                f"{markdown.convert(report['html'])}\n"
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
        value = self.value.loc[days[0] : days[-1]]["Total"]
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
        alt_text = report.partition("\n")[0][2:-2] + " Chart"
        report += (
            f"Holdings have had {difference_string} or {abs(pct_difference):.2f}% "
            f"from the previous period.\n\n"
            f"![{alt_text}](cid:portfolio-summary)\n"
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
                        f"on {date.strftime('%m/%d')}.\n"
                    )
                    for date, shares in change.items()
                    if shares > 0
                ]
            report += "".join(changes)
        return report

    def plot(self, period: str = "w") -> str:
        """Plot the portfolio total and save to an image file."""
        import matplotlib.pyplot as plt
        from pandas.plotting import register_matplotlib_converters

        register_matplotlib_converters()
        fig, ax = plt.subplots(figsize=(8, 6))
        self.value.Total.resample(period).plot.line(
            ax=ax,
            color="blue",
            title="Portfolio Summary",
            ylabel="Value",
            ylim=(self.value.Total.min(), self.value.Total.max()),
        )
        plt.grid(True)
        with tempfile.NamedTemporaryFile(
            dir=".", prefix="portfolio_", suffix=".png", delete=False
        ) as file:
            plt.savefig(file.name, bbox_inches="tight")
            return file.name

    def email(self, args: argparse.Namespace = None) -> bool:
        """Send the portfolio report by email."""
        try:
            server = self.config["email"]["smtp_server"]
            port = self.config["email"]["smtp_port"]
            user = self.config["email"]["smtp_user"]
            password = self.config["email"]["smtp_password"]
            sender = self.config["email"]["sender"]
            recipients = self.config["email"]["recipients"].splitlines()[1:]
        except KeyError:
            print(f"Email configuration incomplete.")
            return False
        message = MIMEMultipart()
        message["From"] = sender
        message["Reply-To"] = sender
        message["To"] = ", ".join(recipients)
        message["Message-ID"] = make_msgid(domain="gmail.com")
        message["Date"] = formatdate(localtime=True)
        message["Subject"] = "Portfolio Report"
        report = self.report(args)
        with open("message.html", "w", encoding="utf-8") as file:
            file.write(report.html)
        content = MIMEMultipart("alternative")
        part1 = MIMEText(report.text, "plain", "utf-8")
        content.attach(part1)
        part2 = MIMEText(report.html, "html", "utf-8")
        content.attach(part2)
        message.attach(content)
        if args.date.dayofweek == 4:
            with open(self.plot(), "rb") as chart_file:
                chart1 = MIMEImage(chart_file.read())
                chart1.add_header(
                    "Content-Disposition", "attachment", filename="portfolio.png"
                )
                chart1.add_header("X-Attachment_Id", "0")
                chart1.add_header("Content-Id", "portfolio-summary")
                message.attach(chart1)
        if args.test:
            print(message.as_string())
            return False
        with smtplib.SMTP(server, int(port)) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
            return True
