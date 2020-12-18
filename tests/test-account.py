import random

import pytest

from context import account
from context import portfolio


@pytest.fixture(scope="module")
def sample_account():
    name = "Sample Account"
    number = "{:010d}".format(random.randint(0, 9999999999))
    pf = portfolio.Portfolio(None, portfolio.test_data(), portfolio.test_holdings())
    return account.Account(number, name, pf)


def test_account_account_number(sample_account):
    """Ensures that the account number is masked."""
    assert sample_account.account_number.startswith("*" * 6)
