from eternity2.direction import Direction


class PatternSvgDefinition:
    def __init__(self, name: str, bg_color: str, bg_stroke: str, path: str | None, path_color: str | None,
                 path_stroke: str | None, direction: Direction = Direction.LEFT):
        self.name = name
        self.bg_color = bg_color
        self.bg_stroke = bg_stroke
        self.path = path
        self.path_color = path_color
        self.path_stroke = path_stroke
        self.direction = direction

    def copy(self):
        return PatternSvgDefinition(self.name, self.bg_color, self.bg_stroke, self.path, self.path_color,
                                    self.path_stroke, self.direction)
