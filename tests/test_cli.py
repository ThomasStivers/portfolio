import pytest
from tests.context import cli


@pytest.fixture(scope="module")
def parser():
    return cli.make_parser()


def test_cli_parse_args(parser):
    return
    argvs = [
        [],
        ["-v"],
        ["-vv"],
        ["-q"],
        ["interactive"],
        ["list"],
        ["-v", "list"],
        ["-vv", "list"],
        ["report"],
        ["update"],
        ["update", "-S", "T", "100", "1/3/2020"],
        ["update", "-A", "T", "100", "1/4/2020"],
        ["update", "-R", "T", "100", "1/5/2020"],
    ]
    for argv in argvs:
        assert parser.parse_args(argv)


def test_cli_interactive(parser):
    pass


def test_cli_list(parser, sample_portfolio):
    argv = ["list"]
    args = parser.parse_args(argv)
    assert callable(args.func)
    assert args.verbosity == 0
    assert args.func(args, sample_portfolio) == "\t".join(
        sample_portfolio.holdings.columns
    )


def test_cli_report(parser, sample_portfolio):
    argv = ["report"]
    args = parser.parse_args(argv)
    assert args.verbosity == 1
    assert not args.email
    assert callable(args.func)
    # assert type(args.func(args, sample_portfolio)) == report.Report


def test_cli_update(parser):
    pass
