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
