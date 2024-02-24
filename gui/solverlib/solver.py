import subprocess
from pathlib import Path

from eternitylib.board import Board
from logger import Logger
from solverlib.execution import Execution


class Solver:
    def __init__(self):
        # exe is in the same dir as this file
        self.logger = Logger(self)
        self.exe_path = Path(__file__).parent / "e2solver"

    def link_solver(self, path: Path = Path(__file__).parent.parent.parent / "cmake-build-debug/solver/Solver"):
        # If file does not exist, raise an error
        if not path.exists():
            self.logger.error(f"Solver executable not found at {path}")
            raise FileNotFoundError(f"Solver executable not found at {path}")

        if self.exe_path.exists():
            self.logger.debug(f"Deleting existing solver at {path}")
            self.exe_path.unlink()

        self.logger.debug(f"Symlinking {path} to {self.exe_path}.")
        self.exe_path.symlink_to(path)

    def solve(self, board: Board, timeout: float = 60) -> Execution:
        # Write the board to a file
        self.logger.info(f"Writing board to tmp/board.{board.hash()}.txt.")
        board_path = Path(__file__).parent.parent / f"tmp/board.{board.hash()}.txt"
        board_path.parent.mkdir(parents=True, exist_ok=True)
        board_path.write_text(board.to_csv())

        try:
            self.logger.info(f"Running solver with timeout of {timeout} seconds")
            result = subprocess.run([self.exe_path, str(board_path)], capture_output=True, timeout=timeout)
            self.logger.info(f"Solver returned with code {result.returncode}")
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Solver timed out after {timeout} seconds")
            return Execution("", timeout=timeout)
        return Execution(result.stdout.decode("utf-8"))
