import sys

import markdown
import pytest
from context import portfolio


def test_portfolio_test_data():
    assert "SAMPLE" in portfolio.test_data().Close.columns


def test_portfolio_test_holdings():
    assert "SAMPLE" in portfolio.test_holdings().columns


@pytest.fixture(scope="module")
def sample_portfolio():
    data = portfolio.test_data()
    holdings = portfolio.test_holdings()
    return portfolio.Portfolio(None, data, holdings)


def test_portfolio_to_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "TEST"
    assert (
        sample_portfolio.to_shares(symbol, 10, date)
        == 10 / sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_to_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "TEST"
    assert (
        sample_portfolio.to_cash(symbol, 10, date)
        == 10 * sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_add_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "TEST"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.add_cash(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value + (
        10 / sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_add_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "TEST"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.add_shares(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value + 10


def test_portfolio_remove_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "TEST"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.remove_cash(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value - (
        10 / sample_portfolio.data.Close.loc[date, symbol]
    )


def test_portfolio_remove_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "TEST"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.remove_shares(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value - 10


def test_portfolio_parse_args(sample_portfolio):
    argv = ["-aceiltv", "--sample"]
    args = sample_portfolio.parse_args(argv)
    assert all(args.symbol == sample_portfolio.holdings.columns)
    assert args.cash
    assert args.email
    assert args.interactive
    assert args.sample
    assert args.test
    assert args.verbose
