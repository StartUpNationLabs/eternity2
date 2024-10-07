import copy
import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List
from uuid import uuid4

from PIL import Image
from PIL import ImageDraw

from eternitylib.pattern import Pattern
from scheduler.solver.v1 import solver_pb2


class Piece:
    _id: int
    is_hint: bool = False

    # init with a list of four patterns
    def __init__(self, patterns: List[Pattern]):
        self._id = uuid4().int

        self.patterns = patterns

        temp = NamedTemporaryFile(delete=False, suffix=".png")

        self.image_path = Path(temp.name)

    def set_hint(self):
        self.is_hint = True

    @property
    def image(self) -> Path:
        # create an image with the four colors
        img = Image.new("RGB", (32, 32))
        draw = ImageDraw.Draw(img)

        # Draw a triancle for each side
        coords = [
            [(32, 0), (16, 16), (0, 0)],
            [(32, 32), (16, 16), (32, 0)],
            [(0, 32), (16, 16), (32, 32)],
            [(0, 0), (16, 16), (0, 32)]
        ]

        for i, pattern in enumerate(self.patterns):
            draw.polygon(
                coords[i],
                fill=pattern.color.hex,
            )

        # Draw a black 1px border
        draw.line([(0, 0), (31, 0), (31, 31), (0, 31), (0, 0)], fill="black")

        if self.is_hint:
            draw.line([(0, 0), (31, 0), (31, 31), (0, 31), (0, 0)], fill="red")

        img.save(self.image_path)

        return Path(self.image_path)

    def rotate90(self, n: int = 1):
        for _ in range(n):
            self.patterns = [self.patterns[3]] + self.patterns[:3]

    def __copy__(self):
        piece = Piece([copy.copy(pattern) for pattern in self.patterns])
        piece.is_hint = self.is_hint
        return piece

    @property
    def id(self):
        return self._id

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f"Piece({self.patterns})"

    @property
    def hash(self):
        return hashlib.md5(".".join(pattern.pattern_code for pattern in self.patterns).encode()).hexdigest()


    def to_grpc(self):
        return solver_pb2.Piece(
            top=int(self.patterns[0].pattern_code, 2),
            right=int(self.patterns[1].pattern_code, 2),
            bottom=int(self.patterns[2].pattern_code, 2),
            left=int(self.patterns[3].pattern_code, 2),

        )