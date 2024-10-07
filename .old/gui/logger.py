import logging
from pathlib import Path


class Logger:
    logger: logging.Logger
    log_folder = Path(__file__).parent / "logs"

    def __init__(self, clazz):
        if not self.log_folder.exists():
            self.log_folder.mkdir()

        self.logger = logging.getLogger(type(clazz).__name__)
        self.logger.setLevel(logging.WARNING)

        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.stream_handler = logging.StreamHandler()
        self.stream_handler.setLevel(logging.INFO)
        self.stream_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.stream_handler)

        self.file_handler = logging.FileHandler(self.log_folder / f"{type(clazz).__name__}.log")
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)