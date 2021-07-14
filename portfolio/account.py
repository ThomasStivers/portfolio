"""Accounts contain holdings of one or more financial instruments."""

import re
from typing import Union

from .portfolio import Portfolio


class Account:
    def __init__(
        self,
        number: Union[int, str],
        portfolio: Portfolio,
        cash: float = 0,
        name: str = None,
        owner: str = None,
    ):
        """Named and numbered account.

        Args:
            number: Minimum of 8 digits. Will be hidden in regular usage.
            portfolio: Contains the holdings of the account.
            cash: Cash held in the account.
            name: Optional name for the account.
            owner: Optional name of the account owner.
        """
        if not re.match(r"^[0-9]{8,}$", str(number)):
            raise (
                ValueError(
                    "Account numbers must be a minimum of 8 digits with no punctuation."
                )
            )
        self._number = str(number)
        self.cash = cash
        self.portfolio = portfolio
        self.name = name
        self.owner = owner

    def __add__(self, cash: float) -> float:
        self.cash += cash
        return self.balance

    def __float__(self) -> float:
        return float(self.balance)

    def __len__(self) -> int:
        """The number of funds held in the account.

        Returns:
            The number of unique instruments this account contains.
        """
        return len(self.portfolio.holdings.columns)

    def __repr__(self) -> str:
        """Returns the repr string for an Account."""
        return f"{self.__class__.__name__}(number={self.number!r})"

    def __str__(self) -> str:
        """Returns the user friendly string for the Account."""
        return f"Account {self.number} worth ${self.balance:,.2f}"

    @property
    def number(self) -> str:
        """Display account number.

        Returns:
            Account numberin masked form: ******1234.
        """
        return "*" * (len(self._number) - 4) + self._number[-4:]

    @property
    def balance(self) -> float:
        """Returns the most recent sum of all cash and investments in the Account."""
        return self.invested + self.cash

    @property
    def invested(self) -> float:
        return self.portfolio.value["Total"].iloc[-1]
