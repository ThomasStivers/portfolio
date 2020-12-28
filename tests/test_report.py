import math

import pytest

from tests.context import portfolio, report


def test_report_get_overall_report(sample_report):
    data = sample_report.get_overall_report()
    keys = {"total", "difference", "pct_difference", "rank_value", "rank_change"}
    assert keys <= data.keys()


def test_report_get_individual_report(sample_report):
    data = sample_report.get_individual_report("MSFT")
    keys = {"total", "difference", "pct_difference", "rank_value", "rank_change"}
    assert keys <= data.keys()


def test_report_get_periodic_report(sample_report):
    data = sample_report.get_periodic_report("7d")
    assert "period" in data


def test_report_get_report_table(sample_report):
    data = sample_report.get_report_table()
    assert "table_text" in data
    assert "table_html" in data


def test_report_email(sample_report, capsys):
    from email import message_from_string

    sample_report.email(test=True)
    captured = capsys.readouterr()
    message = message_from_string(captured.out)
    print(message.as_string())
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
