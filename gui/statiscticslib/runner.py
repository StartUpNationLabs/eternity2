import itertools

import gradio as gr
from eternitylib.board import Board
from logger import Logger
from solverlib.solver import Solver
from statiscticslib.result import Result
from tqdm import tqdm


class Runner:
    sizes: list[int]
    pattern_counts: list[int]
    solver: Solver
    boards: list[Board]
    results: list[Result]
    logger: Logger
    num_samples: int

    def __init__(self, size_range=(4, 8), pattern_count_range=(2, 22), timeout: float = 60, num_samples=10):
        self.logger = Logger(self)
        self.solver = Solver()
        self.boards = []
        self.results = []
        self.timeout = timeout
        self.num_samples = num_samples

        self.set_size_range(*size_range)
        self.set_pattern_count_range(*pattern_count_range)
        self.logger.info(
            f"New Runner of {size_range[0]}x{size_range[0]} to {size_range[1]}x{size_range[1]} size and from {pattern_count_range[0]} to {pattern_count_range[1]} patterns.")

    def generate_boards(self):
        self.logger.info(f"Generating {len(list(itertools.product(self.sizes, self.pattern_counts)))} boards.")
        for size, pattern_count in itertools.product(self.sizes, self.pattern_counts):
            for _ in range(self.num_samples):
                self.logger.debug(f"Genrating {size}x{size} of {pattern_count} patterns.")
                self.boards.append(Board().generate(size, pattern_count))

    def set_size_range(self, size_start, size_end):
        self.logger.info(f"Setting runner size from {size_start} to {size_end}.")
        self.sizes = list(range(size_start, size_end + 1))

    def set_pattern_count_range(self, pattern_count_start, pattern_count_end):
        self.logger.info(f"Setting runner pattern count from {pattern_count_start} to {pattern_count_end}.")
        self.pattern_counts = list(range(pattern_count_start, pattern_count_end + 1))

    def solve_boards(self, progress=gr.Progress(track_tqdm=True)) -> list[Result]:
        if not self.boards:
            self.generate_boards()

        for board in tqdm(self.boards):
            self.logger.debug(f"Solving {board}.")
            self.results.append(Result(board, self.solver.solve(board, timeout=self.timeout)))

        return self.results
