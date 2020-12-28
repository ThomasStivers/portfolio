import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)d: %(message)s",
    datefmt="%m/%d/%y %H:%M %p",
)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
logger.addHandler(stream)
file = logging.FileHandler("portfolio.log", mode="w")
file.setFormatter(formatter)
logger.addHandler(file)
