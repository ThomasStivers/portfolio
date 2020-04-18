Command Line Options
====================

usage: portfolio.py [-h] [-a] [-c] [-d DATE] [-e] [-i] [-l]
                    [-s SYMBOL [SYMBOL ...]] [-t] [-v] [-x EXPORT]
                    [-A SYMBOL SHARES DATE] [-F FILE] [-R SYMBOL SHARES DATE]
                    [--sample]

A tool for managing a stock portfolio.

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             View a report for all holdings.
  -c, --cash            If specified the quantity for the --add or --remove
                        options will be specified as cash otherwise defaults
                        to shares.
  -d DATE, --date DATE  The date to look up.
  -e, --email           Email the portfolio report.
  -i, --interactive     Interactively make changes to the portfolio.
  -l, --list            Displays a list of the symbols available in the
                        portfolio.
  -s SYMBOL [SYMBOL ...], --symbol SYMBOL [SYMBOL ...]
                        The stock ticker symbol(s) to look up.
  -t, --test            Used to test emails without sending.
  -v, --verbose         Provide more detailed information.
  -x EXPORT, --export EXPORT
                        Export holdings to a csv or xlsx file.
  -A SYMBOL SHARES DATE, --add SYMBOL SHARES DATE
                        Add shares of a given symbol for a given date.
  -F FILE, --file FILE  Name of the file where holdings and market data are
                        stored. The default is holdings.h5.
  -R SYMBOL SHARES DATE, --remove SYMBOL SHARES DATE
                        Remove shares of a given symbol for a given date.
  --sample              Only use sample data in the portfolio.
