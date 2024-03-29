from getpass import getpass
from pathlib import Path
from typing import Callable, Dict

import pandas as pd  # type: ignore

from portfolio.config import PortfolioConfig
from portfolio.portfolio import Portfolio
from portfolio.report import Report


class _Interactive(object):
    """Make changes to the portfolio interactively."""

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        self.menu_actions: Dict[int, Callable] = dict()
        self.menu = dict(
            enumerate(
                [
                    "Increase held shares of an existing symbol.",
                    "Decrease held shares of an existing symbol.",
                    "Set the share count for an existing symbol.",
                    "Add a new symbol to the portfolio.",
                    "Create a new portfolio.",
                    "Report on portfolio performance.",
                    "Configure email setup.",
                    "Email portfolio report.",
                    "Export the portfolio to a file.",
                    "Quit",
                ],
                start=1,
            )
        )
        self.assign_actions()
        self.show_menu()

    def show_menu(self) -> None:
        """Display the menu."""
        menu_string = "\n".join(
            [".\t".join([str(choice), item]) for choice, item in self.menu.items()]
        )
        choice = int(input(menu_string + "\n Choice: > "))
        self.menu_actions[choice]()

    def assign_actions(self) -> dict:
        """Assign methods to actions."""
        menu = self.menu
        for id, action in menu.items():
            name = action.lower().split(" ")[0]
            method = getattr(self, name)
            self.menu_actions[id] = method
        return self.menu_actions

    def add(self) -> None:
        """Add a new symbol to the portfolio."""
        symbol = input("Symbol to add: ")
        date = pd.Timestamp(input(f"Date on which to add {symbol}: "))
        quantity = input("Shares to add (preceed with $ for cash value): ")
        if quantity.startswith("$"):
            cash = float(quantity[1:])
            self.portfolio.add_symbol(
                symbol, self.portfolio.to_shares(symbol, cash, date), date
            )
        else:
            shares = float(quantity)
            self.portfolio.add_symbol(symbol, shares, date)
            self.show_menu()

    def configure(self) -> None:
        """Configure email settings."""
        with PortfolioConfig() as config:
            email = config["email"]
        email["smtp_server"] = input(f"SMTP Server ({email['smtp_server']}): ")
        email["smtp_port"] = input(f"SMTP port ({email['smtp_port']}): ")
        email["smtp_user"] = input(f"SMTP User Name ({email['smtp_user']}): ")
        email["smtp_password"] = getpass(
            prompt=f"SMTP Password ({len(email['smtp_password'])* '*'}): "
        )
        email["sender"] = input("From: ")
        recipients = []
        while True:
            recipient = input("To: ")
            if recipient == "":
                break
            recipients.append(recipient)
        if len(recipients) == 1:
            raise ValueError("At least one recipient is required.")
        else:
            email["recipients"] = recipients[1]
        with PortfolioConfig() as config:
            config["email"] = email
        self.show_menu()

    def create(self):
        """Create a new portfolio."""
        filename = input("File name to create: ")
        path = Path(filename)
        if not path.exists():
            self.portfolio = Portfolio(path=path)
            self.add()

    def decrease(self) -> None:
        """Remove shares of a symbol from the portfolio on a given date."""
        symbol = input("Symbol to remove: ")
        date = pd.Timestamp(input(f"Date on which to remove {symbol}: "))
        quantity = input("Shares to remove (preceed with $ for cash value): ")
        if quantity.startswith("$"):
            cash = float(quantity[1:])
            self.portfolio.remove_cash(symbol, cash, date)
        else:
            shares = float(quantity)
            self.portfolio.remove_shares(symbol, shares, date)
            self.show_menu()

    def email(self) -> None:
        """Email the html formatted portfolio report to designated recipients."""
        date = pd.Timestamp(input("Date of report: "))
        with PortfolioConfig() as config:
            Report(self.portfolio, config=config, date=date).email()
        print("Portfolio emailed.")
        self.show_menu()

    def export(self) -> None:
        """Export the holdings in the portfolio to a csv or xlsx file."""
        filename = input("Name of file to export: ")
        self.portfolio.export(filename)
        print(f"Portfolio exported to {filename}.")
        self.show_menu()

    def increase(self):
        """Add shares of a symbol to the portfolio on a given date."""
        symbol = input("Symbol to add: ")
        date = pd.Timestamp(input(f"Date on which to add {symbol}: "))
        quantity = float(input("Shares to add (preceed with $ for cash value): "))
        if quantity.startswith("$"):
            cash = float(quantity[1:])
            self.portfolio.add_cash(symbol, cash, date)
        else:
            shares = float(quantity)
            self.portfolio.add_shares(symbol, shares, date)
            self.show_menu()

    def quit(self) -> None:
        """Quits the interactive session."""
        exit()

    def report(self) -> None:
        """Generate portfolio report interactively."""
        date = pd.Timestamp(input("Date of report: "))
        print(Report(self.portfolio, config=None, date=date).text)
        self.show_menu()

    def set(self) -> None:
        self.show_menu()
