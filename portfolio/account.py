import re

from .portfolio import Portfolio


class Account(object):
    def __init__(
        self, number: str, portfolio: Portfolio, name: str = None, owner: str = None
    ):
        if not re.match(r"^[0-9]{8,}$", number):
            raise (
                ValueError(
                    "Account numbers must be a minimum of 8 digits with no punctuation."
                )
            )
        self._number = str(number)
        self.portfolio = portfolio
        self.name = name
        self.owner = owner

    def __len__(self):
        """The number of funds held in the account."""
        return len(self.portfolio.holdings.columns)

    def __repr__(self):
        return f"{self.__class__.__name__}(number={self.number!r})"

    def __str__(self):
        return f"Account {self.number} worth ${self.balance:,.2f}"

    @property
    def number(self):
        """Display account number in masked form: ******1234."""
        return "*" * (len(self._number) - 4) + self._number[-4:]

    @property
    def balance(self):
        return self.portfolio.value["Total"].iloc[-1]
