from collections import UserDict
import json
from pathlib import Path

from portfolio.log import logger


class PortfolioConfig(UserDict):
    """Defines the sections and options in the portfolio.json file."""

    portfolio_dir = Path.home() / ".portfolio"
    json_config = portfolio_dir / "portfolio.json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.from_json()
            logger.debug("Read config from json=%s", self.json_config)
        except Exception as e:
            logger.exception(e)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.to_json()

    def to_json(self):
        with open(self.json_config, "w") as js:
            json.dump(self.data, js, indent=4)

    def from_json(self):
        with open(self.json_config) as js:
            self.data = json.load(js)
