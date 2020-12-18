import math

import pytest

from context import portfolio, report


@pytest.fixture(scope="module")
def sample_report():
    pf = portfolio.Portfolio(None, portfolio.test_data(), portfolio.test_holdings())
    return report.Report(pf)


def test_report_constructor():
    with pytest.raises(ValueError):
        report.Report(None)


def test_report_get_overall_report(sample_report):
    data = sample_report.get_overall_report()
    keys = {"total", "difference", "pct_difference", "rank_value", "rank_change"}
    assert keys <= data.keys()


def test_report_get_individual_report(sample_report):
    data = sample_report.get_individual_report("MSFT")
    keys = {"total", "difference", "pct_difference", "rank_value", "rank_change"}
    assert keys <= data.keys()


def test_report_get_table_report(sample_report):
    data = sample_report.get_table_report()
    assert data


def test_report_email(sample_report, capsys):
    from email import message_from_string

    sample_report.email(test=True)
    captured = capsys.readouterr()
    message = message_from_string(captured.out)
    assert message.is_multipart()
    for part in message.walk():
        if part.get_content_type() == "text/html":
            assert part.get_payload() == sample_report.html
        elif part.get_content_type() == "text/plain":
            assert part.get_payload() == sample_report.text


def test_ordinal():
    numbers = [1, 2, 3, 4, 10, 11, 12, 13, 14]
    ordinals = ["1st", "2nd", "3rd", "4th", "10th", "11th", "12th", "13th", "14th"]
    assert [report.ordinal(n) for n in numbers] == ordinals


def test_superscript():
    assert report.superscript("1st") == "1<sup>st</sup>"
