import random

import numpy as np
import pandas as pd
import pytest
from tests.context import account, config, portfolio, report


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
    return data.Close


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
    with portfolio.Portfolio("tests/data", data, holdings) as pf:
        return pf


@pytest.fixture(scope="module")
def sample_report(sample_portfolio):
    with config.PortfolioConfig() as conf:
        return report.Report(sample_portfolio, config=conf)


@pytest.fixture(scope="module")
def sample_account(sample_portfolio):
    name = "Sample Account"
    number = "{:010d}".format(random.randint(0, 9999999999))
    return account.Account(number, name, sample_portfolio)
