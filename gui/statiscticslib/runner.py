import itertools

from eternitylib.board import Board
from solverlib.solver import Solver
from statiscticslib.result import Result


class Runner:
    sizes: list[int]
    pattern_counts: list[int]
    solver: Solver
    boards: list[Board]
    results: list[Result]

    def __init__(self, size_range=(4, 8), pattern_count_range=(2, 22)):
        self.solver = Solver()
        self.boards = []
        self.results = []

        self.set_size_range(*size_range)
        self.set_pattern_count_range(*pattern_count_range)

    def generate_boards(self):
        for size, pattern_count in itertools.product(self.sizes, self.pattern_counts):
            self.boards.append(Board().generate(size, pattern_count))

    def set_size_range(self, size_start, size_end):
        self.sizes = list(range(size_start, size_end + 1))

    def set_pattern_count_range(self, pattern_count_start, pattern_count_end):
        self.pattern_counts = list(range(pattern_count_start, pattern_count_end + 1))

    def solve_boards(self) -> list[Result]:
        if not self.boards:
            self.generate_boards()

        for board in self.boards:
            self.results.append(Result(board, self.solver.solve(board)))

        return self.results
