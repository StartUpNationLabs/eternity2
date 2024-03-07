import os

from lxml.etree import _Element
from svg_ultralight import write_svg

from eternity2.direction import Direction
from eternity2.official_patterns import OfficialPatterns
from eternity2.pattern_svg_definition import PatternSvgDefinition
from eternity2.pattern_utils import create_pattern_svg


def save_svg(pattern: PatternSvgDefinition):
    # Get the svg
    svg: _Element = create_pattern_svg(pattern)

    # Save SVG
    # Ensure the output directory exists
    output_dir = "all_patterns"
    os.makedirs(output_dir, exist_ok=True)
    svg_filename = f'{output_dir}/{pattern.name}-{pattern.direction.value}.svg'
    write_svg(svg_filename, svg)

    # Verify the SVG file was saved
    assert os.path.exists(svg_filename), f"SVG file was not saved: {svg_filename}"


def main():
    for pattern in OfficialPatterns:
        pattern_svg_definition = pattern.value.svg

        # Create four patterns for each direction and save them to csv
        for direction in Direction:
            pattern_svg_definition.direction = direction
            save_svg(pattern_svg_definition)


if __name__ == "__main__":
    main()
