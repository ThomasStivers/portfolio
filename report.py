from datetime import datetime

from jinja2 import Environment, PackageLoader, select_autoescape
import pandas as pd
from portfolio import Portfolio


def ordinal(n):
    return "%d%s" % (
        n,
        "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
    )


class Report(object):

    title = "Portfolio Report"

    def __init__(self, pf: Portfolio, date: datetime = datetime.today()):
        if date not in pf.data.index:
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

    def get_overall_report(self) -> dict:
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
        return data

    def get_individual_report(self, symbol: str) -> dict:
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
        return data


if __name__ == "__main__":
    report = Report(Portfolio())
    data = report.data
    print(report.html_template.render(**data))
    print(report.text_template.render(**data))
