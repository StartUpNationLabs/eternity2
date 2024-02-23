from logger import Logger


class Execution:
    def __init__(self, logs: str, timeout: float = None):
        self.logger = Logger(self)
        self.logs = logs
        self.time = 0

        if timeout:
            self.time = timeout
        else:
            self.parse_logs()

    def parse_logs(self):
        # scrape metadata logs
        for line in self.logs.split("\n"):
            self.logger.debug(f"Scraping line: {line}")
            if line.startswith("=time="):
                self.logger.debug(f"Found time line: {line}")
                self.time = float(line.split("=")[2])

        self.logger.debug(f"Execution time: {self.time}")

    def __repr__(self):
        return f"""
Execution:
    Time: {self.time}
        """
    #     Logs: {self.logs}
