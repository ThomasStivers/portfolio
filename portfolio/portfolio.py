"""A tool for managing a stock portfolio."""
import argparse

# from configparser import ConfigParser
from functools import cached_property
from pathlib import Path
import sys
from typing import List, Optional, Union

# Imports for pandas and related modules
import pandas as pd  # type: ignore
from pandas.tseries.holiday import USFederalHolidayCalendar  # type: ignore
from pandas.tseries.offsets import BDay  # type: ignore
import numpy as np  # type: ignore
from pandas_datareader import DataReader  # type: ignore

from portfolio.config import PortfolioConfig
from portfolio.log import logger


# Pandas options
pd.set_option("display.float_format", "{:,.2f}".format)
pd.set_option("colheader_justify", "center")


class Portfolio:
    """Provides information about a portfolio of financial instruments."""

    def __init__(
        self,
        path: str = None,
        data: pd.DataFrame = pd.DataFrame(),
        holdings: pd.DataFrame = pd.DataFrame(),
    ):
        """Initialize the portfolio with holdings and market data.

        Args:
            path: The name of an a directory containing holdings and market data. If this
                is None then the portfolio must be described by the data and holdings arguments.
            data: A DataFrame  containing market close data for a set of
                financial instruments over a period of time.
            holdings:   A DataFrame containing the number of shares held of the set of
                symbols in data over a time period corresponding to that of data.
        """
        if len(data) > 0 and len(holdings) > 0:
            logger.debug("Data and holdings arguments are set.")
            self.data = data
            self.holdings = holdings
        else:
            logger.debug("Data and holdings are not set.")
        if path is None:
            path = Path().home() / ".portfolio" / "data"
        self.path = Path(path)
        if not self.path.is_dir():
            logger.info("%s is not a directory, creating it...", self.path)
            self.path.mkdir()
        self.data_file = self.path / "prices.feather"
        self.holdings_file = self.path / "holdings.feather"
        try:
            # The feather format does not support date indices,
            # so set the Date colemn to be the index.
            self.holdings = pd.read_feather(self.holdings_file).set_index("date")
        except FileNotFoundError:
            logger.info("No stored holdings found.")
            self.holdings = holdings
        symbols = self.holdings.columns
        try:
            # The feather format does not support date indices,
            # so set the Date colemn to be the index.
            self.data = pd.read_feather(self.data_file).set_index("date")
        except FileNotFoundError:
            logger.info("Market data is not stored .")
        calendar = USFederalHolidayCalendar()
        today = pd.Timestamp.today().normalize()
        last_business_day = min(today - BDay(1), self.data.index.max() + BDay(1))
        holidays = calendar.holidays(last_business_day, today)
        if (
            today not in self.data.index
            and last_business_day not in self.data.index
            and holidays.empty
        ):
            self.data = self.get_market_data(
                symbols,
                start=last_business_day,
                end=today,
            )
            self.holdings = self.holdings.reindex(
                self.data.index, method="ffill"
            ).dropna()

    @cached_property
    def value(self) -> pd.DataFrame:
        """The value of the held shares at closing on each date.

        Returns:
            The market closing price of all instruments multiplied by the number of held
            shares for all dates. Includes a Totals column with the value of all shares held on a given date.
        """
        value = self.data * self.holdings.fillna(method="bfill")
        value["Total"] = value.sum(axis=1)
        return value

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """Stores market and holdings data to an feather file."""
        saved_data = pd.read_feather(self.data_file)
        saved_holdings = pd.read_feather(self.holdings_file)
        if not saved_data.equals(self.data.reset_index()):
            logger.debug("Writing market data to %s...", self.data_file)
            self.data.reset_index().to_feather(self.data_file)
        if not saved_holdings.equals(self.holdings.reset_index()):
            logger.debug("Writing holdings to %s...", self.holdings_file)
            self.holdings.reset_index().to_feather(self.holdings_file)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"path={self.path!r}, data={self.data!r}, holdings={self.holdings!r})"
        )

    def __str__(self) -> str:
        """Briefly describe the holdings in the portfolio in a string.

        Returns:
            A string briefly summarizing the contents of the portfolio."""
        return (
            f"Portfolio holding {self.holdings.shape[1]} instruments "
            f"for {self.holdings.shape[0]} dates "
            f"worth ${self.value.Total.iloc[-1]:,.2f}."
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
                f"{symbol} is already inportfolio. Use add_shares or add_cash instead."
            )
        self.holdings.loc[date:, symbol] = quantity
        try:
            self.data[symbol] = self.get_market_data(list(symbol))
        except KeyError:
            logger.debug("Unable to retrieve market data for %s.", symbol)

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
        prices = self.data[symbol]
        date_index = prices.index.get_loc(date, method="ffill")
        date = prices.index[date_index]
        price = prices[date]
        cash = shares * price
        return cash

    def to_shares(self, symbol: str, cash: float, date: pd.Timestamp) -> float:
        """Get the number of shares of an instrument purchasable for a given price on a given date.

        :param symbol: The ticker symbol to get the share count.
        :param cash: The number of dollars to get the share count for.
        :param date: The date whose closing price should be used.

        :returns: The count of  shares of symbol purchasable for cash on the specified date.
        """
        last_close = self.data.iloc[self.data.index.get_loc(date, method="ffill")][
            symbol
        ]
        shares = cash / last_close
        return shares

    def export(self, filename: str = "holdings.csv") -> bool:
        """Export the holdings in the portfolio to a file.

        Args:
            filename: A CSV or XLSX file where holdings data should be exported.
        """
        logger.debug("Exporting data to %s...", filename)
        if filename.endswith(".csv"):
            self.holdings.drop_duplicates().to_csv(filename)
            return True
        elif filename.endswith(".xlsx"):
            with pd.ExcelWriter(filename, datetime_format="mm/dd/yyyy") as writer:
                self.data.to_excel(writer, sheet_name="Prices")
                self.holdings.drop_duplicates().to_excel(writer, sheet_name="Holdings")
                self.value.to_excel(writer, sheet_name="Value")
                return True
        return False

    def get_market_data(
        self,
        symbols: List[str],
        start: Union[str, pd.Timestamp] = None,
        end: Union[str, pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """Retrieve stock market information from IEX Cloud.

        Args:
            symbols: Stock ticker symbols to look up.
            start: The first date that will be included in the results.
            end: The last date that will be included in results

        Returns:
            The closing prices for the provided symbols over the date range.
        """
        with PortfolioConfig() as config:
            try:
                last_retrieval = pd.to_datetime(config["iex"]["last_retrieval"])
            except KeyError:
                last_retrieval = pd.Timestamp(0)
            api_key = config["iex"]["api_key"]
        today = pd.Timestamp.today().normalize()
        latest_data = self.data.index.max()
        if len(symbols) == 0:
            logger.info("Nothing to retrieve.")
            return pd.DataFrame()
        else:
            symbols = list(symbols)
        if latest_data < today - BDay(1) and last_retrieval < today:
            logger.info(
                "Retrieving market data for %s through %s from IEX Cloud...",
                start.strftime("%x"),
                end.strftime("%x"),
            )
            data = DataReader(list(symbols), "iex", start, end, api_key=api_key)
            if data.empty:
                logger.warn("No data retrieved.")
                return self.data
            with PortfolioConfig() as config:
                config["iex"]["last_retrieval"] = str(today)
            data.index = pd.to_datetime(data.index)
            try:
                self.data = self.data.append(data.close, verify_integrity=True)
            except ValueError:
                logger.warn(
                    "The portfolio already contains data for the period %s through %s.",
                    start.strftime("%x"),
                    end.strftime("%x"),
                )
            return self.data
        else:
            return self.data
