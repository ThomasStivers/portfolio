from datetime import datetime
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import smtplib

from jinja2 import Environment, PackageLoader, select_autoescape
import pandas as pd
from .portfolio import Portfolio


def ordinal(n: int) -> str:
    """Produces ordinal numbers (1st, 2nd, 3rd)."""
    return "%d%s" % (
        n,
        "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
    )


def superscript(ord: str) -> str:
    """Converts the suffix of ordinal numbers to superscript in html."""
    return ord.replace(ord[-2:], f"<sup>{ord[-2:]}</sup>")


class Report(object):

    title = "Portfolio Report"

    def __init__(self, pf: Portfolio, config, date: datetime = datetime.today()):
        """Constructs a report for the given Portfolio object."""
        if type(pf) != Portfolio:
            raise (ValueError("First argument must be of type portfolio.Portfolio"))
        if date not in pf.data.index:
            self.config = config
            self.date = pf.data.index[
                pf.data.index.get_loc(pd.Timestamp(date), method="nearest")
            ]
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
        self.html_template = self.env.get_template("email/html.html")
        self.text_template = self.env.get_template("email/plain.txt")
        self.data.update(self.get_overall_report())
        self.data["symbols"] = {}
        for symbol in pf.holdings.columns:
            self.data["symbols"][symbol] = {}
            self.data["symbols"][symbol].update(self.get_individual_report(symbol))
        self.data.update(self.get_report_table())
        if self.date.dayofweek == 4:
            self.data["chart_file"] = self.pf.plot()

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"{self.__class__.__name__}(portfolio={self.pf!r}, date={self.date!r})"

    def get_overall_report(self) -> dict:
        """Creates a report including data about the portfolio as a whole."""
        date = self.date
        pf = self.pf
        data = {
            "total": pf.value["Total"].loc[date],
            "difference": pf.value["Total"].diff()[date],
            "pct_difference": pf.value["Total"].pct_change(1)[date] * 100,
            "rank_change": ordinal(
                int(pf.value["Total"].diff().rank(ascending=False)[date])
            ),
            "rank_value": ordinal(int(pf.value["Total"].rank(ascending=False)[date])),
        }
        data["rank_change_html"] = superscript(data["rank_change"])
        data["rank_value_html"] = superscript(data["rank_value"])
        return data

    def get_individual_report(self, symbol: str) -> dict:
        """Generates a dictionary containing data about a single symbol."""
        date = self.date
        pf = self.pf
        if pf.value.loc[date, symbol] == 0:
            del self.data["symbols"][symbol]
            return {}
        data = {
            "total": pf.value.loc[date, symbol],
            "difference": pf.value[symbol].diff()[date],
            "pct_difference": pf.value[symbol].pct_change(1)[date] * 100,
            "rank_change": ordinal(
                int(pf.value[symbol].diff().rank(ascending=False)[date])
            ),
            "rank_value": ordinal(int(pf.value[symbol].rank(ascending=False)[date])),
        }
        data["rank_change_html"] = superscript(data["rank_change"])
        data["rank_value_html"] = superscript(data["rank_value"])
        return data

    def get_report_table(self) -> dict:
        """Makes a table of the values of symbols and their total for a range of dates."""
        data = {}
        date = self.date
        symbols = self.data["symbols"].keys()
        value = self.pf.value
        table_range = value.index[
            value.index.get_loc(date) - 4 : value.index.get_loc(date) + 6
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

    def email(self, test: bool = False) -> bool:
        """Send the portfolio report by email."""
        date = self.date
        try:
            server = self.config["email"]["smtp_server"]
            port = self.config["email"]["smtp_port"]
            user = self.config["email"]["smtp_user"]
            password = self.config["email"]["smtp_password"]
            sender = self.config["email"]["sender"]
            recipients = self.config["email"]["recipients"].splitlines()[1:]
        except KeyError:
            print("Email configuration incomplete.")
            return False
        message = MIMEMultipart()
        message["From"] = sender
        message["Reply-To"] = sender
        message["To"] = ", ".join(recipients)
        message["Message-ID"] = make_msgid(domain="gmail.com")
        message["Date"] = formatdate(localtime=True)
        message["Subject"] = "Portfolio Report"
        with open("message.html", "w", encoding="utf-8") as file:
            file.write(self.html)
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
            print(message.as_string())
            return False
        with smtplib.SMTP(server, int(port)) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
            return True

    @property
    def html(self):
        return self.html_template.render(**self.data)

    @property
    def text(self):
        return self.text_template.render(**self.data)
