import hashlib
from pathlib import Path
from typing import List

from PIL import Image
from PIL import ImageDraw

from eternitylib.pattern import Pattern


class Piece:
    # init with a list of four patterns
    def __init__(self, patterns: List[Pattern]):
        self.patterns = patterns
        if not Path("./tmp").exists():
            Path("./tmp").mkdir()
        self.image_path = Path(f"./tmp/tmp.{self.hash}.png")

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

        img.save(self.image_path)

        return Path(self.image_path)

    def __repr__(self):
        return f"Piece({self.patterns})"

    @property
    def hash(self):
        return hashlib.md5(".".join(pattern.pattern_code for pattern in self.patterns).encode()).hexdigest()
