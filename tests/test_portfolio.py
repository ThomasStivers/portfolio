import sys

import numpy as np
import pandas as pd
import pytest
from context import cli
from context import portfolio


def test_data(symbols=["GOOG", "MSFT"]) -> pd.DataFrame:
    """Generate sambple data.

    :returns: A `DataFrame` containing 5 days worth of random values for 2 sample symbols.

    """
    data = pd.DataFrame(
        data=10 * np.random.randn(5, 6 * len(symbols)) + 100,
        index=pd.date_range("2020-01-01", periods=5, freq="b"),
        columns=pd.MultiIndex.from_product(
            iterables=[
                ["Adj Close", "Close", "High", "Low", "Open", "Volume"],
                symbols,
            ],
            names=["Attributes", "Symbols"],
        ),
    )
    return data


def test_holdings(symbols=["GOOG", "MSFT"]) -> pd.DataFrame:
    """Generate sample holdings."""
    holdings = pd.DataFrame(
        data=np.random.randn(5, len(symbols)) + 10,
        index=pd.date_range("2020-01-01", periods=5, freq="b"),
        columns=symbols,
    )
    return holdings


@pytest.fixture(scope="module")
def sample_portfolio():
    data = test_data()
    holdings = test_holdings()
    return portfolio.Portfolio(None, data, holdings)


def test_portfolio_to_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    assert (
        sample_portfolio.to_shares(symbol, 10, date)
        == 10 / sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_to_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    assert (
        sample_portfolio.to_cash(symbol, 10, date)
        == 10 * sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_add_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.add_cash(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value + (
        10 / sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_add_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.add_shares(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value + 10


def test_portfolio_add_symbol(sample_portfolio):
    sample_portfolio.add_symbol("T", 100, "1/2/2020")
    assert sample_portfolio.holdings.loc["1/2/2020", "T"] == 100
    assert sample_portfolio.data.Close.loc["1/2/2020", "T"] > 0


def test_portfolio_remove_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.remove_cash(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value - (
        10 / sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_remove_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.remove_shares(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value - 10


def test_cli_parse_args():
    argv = ["-aceiltv", "--sample"]
    parser = cli.make_parser()
    args = parser.parse_args(argv)
    assert args.symbol == "all"
    assert args.cash
    assert args.email
    assert args.interactive
    assert args.list
    assert args.sample
    assert args.test
    assert args.verbose


def test_portfolio_value(sample_portfolio):
    assert all(
        sample_portfolio.value["Total"]
        == (sample_portfolio.data.Close * sample_portfolio.holdings).sum(axis=1)
    )
    assert all(
        sample_portfolio.value.drop(columns="Total")
        == sample_portfolio.data.Close * sample_portfolio.holdings
    )
