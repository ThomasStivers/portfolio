import pytest

from tests.context import account
from tests.context import portfolio


def test_account_account_number(sample_account):
    """Ensures that the account number is masked."""
    assert sample_account.number.startswith("*" * 6)
