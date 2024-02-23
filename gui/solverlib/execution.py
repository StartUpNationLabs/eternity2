class Execution:
    def __init__(self, logs: str):
        self.logs = logs
        self.time = 0
        self.parse_logs()

    def parse_logs(self):
        # scrape metadata logs
        for line in self.logs.split("\n"):
            if line.startswith("=time="):
                self.time = float(line.split("=")[2])

    def __repr__(self):
        return f"""
Execution:
    Time: {self.time}
        """
    #     Logs: {self.logs}
