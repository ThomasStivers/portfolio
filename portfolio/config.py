from configparser import ConfigParser
import json
from pathlib import Path

from portfolio.log import logger


class PortfolioConfig(ConfigParser):
    """Defines the sections and options in the portfolio.ini file."""

    portfolio_dir = Path.home() / ".portfolio"
    private_config = portfolio_dir / "portfolio.ini"
    system_config = Path(Path(__file__).parent.parent / "portfolio.ini")
    json_config = portfolio_dir / "portfolio.json"

    def __init__(self):
        super().__init__()
        logger.debug(
            "Reading ini files: user=%s and system=%s...",
            self.private_config,
            self.system_config,
        )
        self.read([self.private_config, self.system_config])
        try:
            self.update(self.from_json())
            logger.debug("Read config from json=%s", self.json_config)
        except Exception as e:
            logger.exception(e)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.to_json()

    def to_json(self):
        serializable = {}
        serializable["DEFAULTS"] = self.defaults()
        for s in self.sections():
            serializable[s] = {}
            for o in self.options(s):
                if o == "recipients":
                    serializable[s][o] = self[s][o].split("\n")[1:]
                elif o not in serializable["DEFAULTS"]:
                    serializable[s][o] = self[s][o]
        with open(self.json_config, "w") as js:
            json.dump(serializable, js, indent=4)
        return json.dumps(serializable, indent=4)

    def from_json(self):
        with open(self.json_config) as js:
            deserialized = json.load(js)
            return deserialized
