import configparser
from datetime import datetime
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from functools import cached_property
import smtplib
import tempfile
from typing import Dict, Optional

from jinja2 import Environment, PackageLoader, select_autoescape
import matplotlib.pyplot as plt  # type: ignore
import pandas as pd  # type: ignore
from pandas.plotting import register_matplotlib_converters  # type: ignore

from portfolio.log import logger
from portfolio.portfolio import Portfolio


def ordinal(n: int) -> str:
    """Produces ordinal numbers (1st, 2nd, 3rd)."""
    return "%d%s" % (
        n,
        "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
    )


def superscript(ord: str) -> str:
    """Converts the suffix of ordinal numbers to superscript in html."""
    if ord == "":
        return ""
    return ord.replace(ord[-2:], f"<sup>{ord[-2:]}</sup>")


class Report:
    """ A report for a portfolio of financial instruments."""

    title = "Portfolio Report"

    def __init__(
        self,
        pf: Portfolio,
        config: Optional[configparser.ConfigParser] = None,
        date: datetime = datetime.today(),
    ):
        """Constructs a report for the given Portfolio object."""
        if type(pf) != Portfolio:
            raise (ValueError("First argument must be of type portfolio.Portfolio"))
        if date not in pf.data.index:
            self.config = config
            self.date = pf.data.index[
                pf.data.index.get_loc(pd.Timestamp(date), method="nearest")
            ]
        else:
            self.date = pd.Timestamp(date)
        self.data = {
            "date": self.date.strftime("%B %d"),
            "title": self.title,
        }
        self.pf = pf
        self.env = Environment(
            loader=PackageLoader("portfolio", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            lstrip_blocks=True,
            trim_blocks=True,
        )
        self.html_template = self.env.get_template("email/portfolio.html")
        self.text_template = self.env.get_template("email/portfolio.txt")
        self.data.update(self.get_overall_report())
        self.data["symbols"] = {}
        for symbol in pf.holdings.columns:
            self.data["symbols"][symbol] = {}
            self.data["symbols"][symbol].update(self.get_individual_report(symbol))
        self.data.update(self.get_report_table())
        if self.date.dayofweek == 4:
            self.data["periodic"] = self.get_periodic_report("7d")
            self.data["chart_file"] = self.plot()

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(portfolio={self.pf!r}, date={self.date!r})"

    def get_overall_report(self) -> Dict[str, str]:
        """Creates a report including data about the portfolio as a whole.

        Returns:
            A dictionary suitable for passing into a jinja2 template to generate a text or html report.
        """
        date = self.date
        pf = self.pf
        start = year_start = pd.Timestamp(date.year, 1, 1)
        if pf.value.index.min() > year_start:
            start = pf.value.index.min()
        end = year_end = pd.Timestamp(date.year, 12, 31)
        if pf.value.index.max() < year_end:
            end = pf.value.index.max()
        data = {
            "total": pf.value["Total"].loc[date],
            "difference": pf.value["Total"].diff()[date],
            "pct_difference": pf.value["Total"].pct_change(1)[date] * 100,
            "rank_change": ordinal(
                int(pf.value.loc[start:end, "Total"].diff().rank(ascending=False)[date])
            ),
            "rank_value": ordinal(
                int(pf.value.loc[start:end, "Total"].rank(ascending=False)[date])
            ),
            "start": start,
            "end": end,
            "days": len(pf.value.loc[start:end]),
        }
        data["rank_change"] = (
            "" if data["rank_change"] == "1st" else data["rank_change"]
        )
        data["rank_value"] = "" if data["rank_value"] == "1st" else data["rank_value"]
        data["rank_change_html"] = superscript(data["rank_change"])
        data["rank_value_html"] = superscript(data["rank_value"])
        return data

    def get_individual_report(self, symbol: str) -> Dict[str, str]:
        """Generates a dictionary containing data about a single symbol.

        Args:
            symbol: A single stock symbol for which to generate a report.

        Returns:
            A dictionary suitable for passing into a jinja2 template to generate a text or html report.
        """
        date = self.date
        pf = self.pf
        if pf.value.loc[date, symbol] == 0:
            del self.data["symbols"][symbol]
            return {}
        start = year_start = pd.Timestamp(date.year, 1, 1)
        if pf.value.index.min() > year_start:
            start = pf.value.index.min()
        end = year_end = pd.Timestamp(date.year, 12, 31)
        if pf.value.index.max() < year_end:
            end = pf.value.index.max()
        data = {
            "total": pf.value.loc[date, symbol],
            "difference": pf.value[symbol].diff()[date],
            "pct_difference": pf.value[symbol].pct_change(1)[date] * 100,
            "rank_change": ordinal(
                int(pf.value.loc[start:end, symbol].diff().rank(ascending=False)[date])
            ),
            "rank_value": ordinal(
                int(pf.value.loc[start:end, symbol].rank(ascending=False)[date])
            ),
            "start": start,
            "end": end,
            "days": len(pf.value.loc[start:end]),
        }
        data["rank_change"] = (
            "" if data["rank_change"] == "1st" else data["rank_change"]
        )
        data["rank_value"] = "" if data["rank_value"] == "1st" else data["rank_value"]
        data["rank_change_html"] = superscript(data["rank_change"])
        data["rank_value_html"] = superscript(data["rank_value"])
        return data

    def get_report_table(self) -> Dict[str, str]:
        """Makes a table of the values of symbols and their total for a range of dates."""
        data = {}
        date = self.date
        symbols = self.data["symbols"].keys()
        value = self.pf.value
        table_range = value.index[
            value.index.get_loc(date) - 4
            if value.index.get_loc(date) - 4 >= 0
            else 0 : value.index.get_loc(date) + 6
        ]
        table_data = value.loc[table_range, symbols]
        # If we only have 0 values don't show the symbol.
        table_data = table_data.loc[:, (table_data != 0).any(axis=0)]
        table_data["Total"] = table_data.sum(axis=1)
        table_data = table_data.T
        table_headers = table_range.strftime("%b-%d")
        table_data.columns = table_headers
        data["table_html"] = table_data.to_html(
            float_format="${:,.2f}".format, classes="symbol_table"
        )
        data["table_text"] = table_data.to_string(float_format="${:,.2f}".format)
        return data

    def get_periodic_report(
        self, period: pd.offsets.DateOffset = "7d"
    ) -> Dict[str, str]:
        """Produce a text string for a given period to be included in the larger portfolio report.

        Args:
            period: The period of time which should be included in the report.

        Returns:
            Data to be used by the report template.
        """
        days = pd.date_range(self.date - pd.Timedelta(period), self.date)
        pf = self.pf
        value = pf.value
        data = {
            "period": ("Weekly" if period == "7d" else "Monthly"),
            "start": days[0].strftime("%m/%d"),
            "end": days[-1].strftime("%m/%d"),
            "value": value.loc[days[0] : days[-1]]["Total"],
            "difference": value.loc[days[0] : days[-1]]["Total"].diff().sum(),
            "pct_difference": value.loc[days[0] : days[-1]]["Total"].pct_change(1).sum()
            * 100,
        }
        range = pf.holdings.loc[days[0] : days[-1]].drop_duplicates().diff().dropna()
        if range.any().any():
            data["changes"] = {}
            for row in range.iterrows():
                data["changes"][row[0]] = {}
                for col in range.columns:
                    if range.loc[row[0], col] != 0:
                        data["changes"][row[0]][col] = range.loc[row[0], col]
        return data

    def email(self, test: bool = False) -> bool:
        """Send the portfolio report by email.

        Args:
            test: True if the email should only be prepared and printed but not sent.

        Returns:
            True if an email was actually sent, False otherwise.
        """
        date = self.date
        config = self.config
        if not config:
            logger.error("Configuration required to send email.")
            return False
        try:
            server = config["email"]["smtp_server"]
            port = config["email"]["smtp_port"]
            user = config["email"]["smtp_user"]
            password = config["email"]["smtp_password"]
            sender = config["email"]["sender"]
            recipients = config["email"]["recipients"].splitlines()[1:]
        except KeyError:
            logger.exception("Email configuration incomplete.")
            return False
        message = MIMEMultipart()
        message["From"] = sender
        message["Reply-To"] = sender
        message["To"] = ", ".join(recipients)
        message["Message-ID"] = make_msgid(domain="gmail.com")
        message["Date"] = formatdate(localtime=True)
        message["Subject"] = "Portfolio Report"
        content = MIMEMultipart("alternative")
        part1 = MIMEText(self.text, "plain", "us-ascii")
        content.attach(part1)
        part2 = MIMEText(self.html, "html", "us-ascii")
        content.attach(part2)
        message.attach(content)
        if date.dayofweek == 4:
            chart1 = MIMEImage(open(self.data["chart_file"], "rb").read())
            chart1.add_header(
                "Content-Disposition", "attachment", filename="portfolio.png"
            )
            chart1.add_header("X-Attachment_Id", "0")
            chart1.add_header("Content-Id", "portfolio-summary")
            message.attach(chart1)
        if test:
            logger.debug("Testing only; email not sent.")
            print(message.as_string())
            return False
        with smtplib.SMTP(server, int(port)) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
            return True

    def plot(self, period: str = "w") -> str:
        """Plot the portfolio total and save to an image file.

        Args:
            period: The period of time to plot, defaults to weeks.

        Returns:
            Name of the file containing the plotted data.
        """
        register_matplotlib_converters()
        pf = self.pf
        fig, ax = plt.subplots(figsize=(8, 6))
        pf.value.Total.resample(period).plot.line(
            ax=ax,
            color="blue",
            title="Portfolio Summary",
            ylabel="Value",
            ylim=(pf.value.Total.min(), pf.value.Total.max()),
        )
        plt.grid(True)
        with tempfile.NamedTemporaryFile(
            dir=pf.path, prefix="portfolio_", suffix=".png", delete=False
        ) as file:
            logger.debug("Saving portfolio chart to %s...", file.name)
            plt.savefig(file.name, bbox_inches="tight")
            return file.name

    @cached_property
    def html(self):
        return self.html_template.render(**self.data)

    @cached_property
    def text(self):
        return self.text_template.render(**self.data)
