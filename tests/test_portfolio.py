import sys

import numpy as np
import pandas as pd
import pytest
from tests.context import cli
from tests.context import portfolio


def test_portfolio_to_shares(sample_portfolio):
    date = "1/6/2020"
    quantity = 10
    symbol = "MSFT"
    assert (
        sample_portfolio.to_shares(symbol, quantity, date)
        == quantity / sample_portfolio.data.loc[date, symbol]
    )


def test_portfolio_to_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    assert (
        sample_portfolio.to_cash(symbol, 10, date)
        == 10 * sample_portfolio.data.loc[date, symbol]
    )


def test_portfolio_add_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.add_cash(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value + (
        10 / sample_portfolio.data.loc[date, symbol]
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
    assert sample_portfolio.data.loc["1/2/2020", "T"] > 0


def test_portfolio_remove_cash(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.remove_cash(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value - (
        10 / sample_portfolio.data.loc[date, symbol]
    )


def test_portfolio_remove_shares(sample_portfolio):
    date = "1/6/2020"
    symbol = "MSFT"
    old_value = sample_portfolio.holdings.loc[date, symbol]
    sample_portfolio.remove_shares(symbol, 10, date)
    assert sample_portfolio.holdings.loc[date, symbol] == old_value - 10


def test_portfolio_value(sample_portfolio):
    assert all(
        sample_portfolio.value["Total"]
        == (sample_portfolio.data * sample_portfolio.holdings).sum(axis=1)
    )
    assert all(
        sample_portfolio.value.drop(columns="Total")
        == sample_portfolio.data * sample_portfolio.holdings
    )


def test_portfolio_get_market_data():
    symbols = ["T", "GE"]
    data = portfolio.Portfolio.get_market_data(symbols)
    assert len(data) > 0
    assert data.columns == symbols
