from eternitylib.board import Board
from solverlib.execution import Execution


class Result:
    def __init__(self, board: Board, execution: Execution):
        self.board = board
        self.execution = execution

    def __repr__(self):
        return f"""
Result:
    Board: {self.board}
    Execution: {self.execution}
        """
