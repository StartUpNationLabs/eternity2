from functools import lru_cache
from typing import List

from colour import Color


@lru_cache
def get_gradient(pattern_count: int) -> List[Color]:
    """Get a gradient of colors from red to blue. First color is grey, then red and last is blue."""
    return list(Color("red").range_to(Color("blue"), pattern_count))


class Pattern:
    def __init__(self, pattern_code: str, pattern_count: int = 23):
        self.pattern_color = Color("gray") if all(bit == "1" for bit in pattern_code.strip()) else \
            get_gradient(pattern_count)[int(pattern_code, 2)]
        self.pattern_code = pattern_code

    def __copy__(self):
        return Pattern(self.pattern_code)

    @property
    def color(self) -> Color:
        return self.pattern_color
