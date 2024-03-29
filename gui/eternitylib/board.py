import copy
import hashlib
import random
from math import sqrt
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image
from eternitylib.pattern import Pattern
from eternitylib.piece import Piece


def generate_inner_symbols(size, number_of_symbols):
    vertical_symbols = np.random.randint(1, number_of_symbols, size=(size, size - 1))
    horizontal_symbols = np.random.randint(1, number_of_symbols, size=(size - 1, size))

    return vertical_symbols, horizontal_symbols


class Board:
    def __init__(self):
        self.pieces: list[Piece] = []
        self._size = 0
        self._pattern_count = 0
        self.hints = []

    def generate(self, size: int, pattern_count: int):
        board = [[None for _ in range(size)] for _ in range(size)]
        vertical_symbols, horizontal_symbols = generate_inner_symbols(size, pattern_count)

        for i in range(size):
            for j in range(size):
                top = "1111111111111111" if i == 0 else format(horizontal_symbols[i - 1, j], '016b')
                bottom = "1111111111111111" if i == size - 1 else format(horizontal_symbols[i, j], '016b')
                left = "1111111111111111" if j == 0 else format(vertical_symbols[i, j - 1], '016b')
                right = "1111111111111111" if j == size - 1 else format(vertical_symbols[i, j], '016b')
                board[i][j] = [top, right, bottom, left]

        self._size = size
        self._pattern_count = pattern_count

        for line in board:
            for piece in line:
                self.add_piece(Piece([Pattern(pattern, pattern_count) for pattern in piece]))

        return self

    def generate_hints(self):
        if self.size < 5:
            raise ValueError("Board too small for hints")

        indexes = [
            (self.size // 2, self.size // 2),                           # Center
            (self.size // 4, self.size // 4),                           # Top Left
            (self.size // 4, self.size - self.size // 4),               # Top Right
            (self.size - self.size // 4, self.size // 4),               # Bottom Left
            (self.size - self.size // 4, self.size - self.size // 4)    # Bottom Right
        ]

        self.hints = [(index, self.pieces[index[0] * self.size + index[1]]) for index in indexes]

        for hint in self.hints:
            hint[1].set_hint()

    def shuffle(self):
        # Return shuffled list if pieces
        self.pieces = sorted(self.pieces, key=lambda x: random.random())
        for piece in self.pieces:
            if not piece.is_hint:
                piece.rotate90(random.randint(0, 3))

    def add_piece(self, piece: Piece):
        self.pieces.append(piece)

    @property
    def size(self):
        return self._size

    @property
    def pattern_count(self):
        return self._pattern_count

    def read_csv(self, csv: str):
        self._size = sqrt(len([line for line in csv.split("\n") if line.strip()]))

        if self._size != int(self._size):
            raise ValueError("Invalid board size")

        self._size = int(self._size)

        self._pattern_count = len(
            set(pattern for line in csv.split("\n") if line.strip() for pattern in line.split(","))
        )

        for i, line in enumerate(csv.split("\n")):
            if line.strip() == "":
                continue

            self.add_piece(Piece([Pattern(pattern, self.pattern_count) for pattern in line.split(",")]))

    def to_csv(self):
        out = f"{self.size}\n"
        for i, piece in enumerate(self.pieces):
            out += f"{','.join(pattern.pattern_code for pattern in piece.patterns)}"
            if self.hints:
                if piece in [hint[1] for hint in self.hints]:
                    hint = [hint for hint in self.hints if hint[1] == piece][0]
                    out += f",1,{hint[0][0]},{hint[0][1]}"
            else:
                out += ",0,0,0"
            out += "\n" if i != len(self.pieces) - 1 else ""

        return out

    def read_file(self, file: Path):
        text = file.read_text()
        self.read_csv(text)

    def hash(self):
        return hashlib.md5(".".join(piece.hash for piece in self.pieces).encode()).hexdigest()

    @property
    def image(self) -> Path:
        img = Image.new("RGB", (self.size * 32, self.size * 32))

        for i, piece in enumerate(self.pieces):
            corners = (
                i % self.size * 32,
                i // self.size * 32,
                (i % self.size + 1) * 32,
                (i // self.size + 1) * 32,
            )

            img.paste(
                Image.open(piece.image),
                corners,
            )

        # Create Temporary file
        file = NamedTemporaryFile(delete=False, suffix=".png")
        img.save(file.name)

        return Path(file.name)

    def __repr__(self):
        return f"Board: {self.size}x{self.size}, {self.pattern_count} patterns"

    def __copy__(self):
        board = Board()
        board._size = self.size
        board._pattern_count = self.pattern_count
        board.pieces = [copy.copy(piece) for piece in self.pieces]
        return board


def main():
    board = Board()
    board.generate(5, 5)
    board.generate_hints()
    print(board.hints)


if __name__ == "__main__":
    main()
