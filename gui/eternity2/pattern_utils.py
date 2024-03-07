from lxml.etree import _Element
from svg_ultralight import new_element, new_sub_element

from eternity2.direction import Direction
from eternity2.pattern_svg_definition import PatternSvgDefinition


def create_pattern_svg(pattern: PatternSvgDefinition) -> _Element:
    # Create SVG root element
    svg = new_element('svg', xmlns="http://www.w3.org/2000/svg", version="1.1", width="256", height="256",
                      viewBox="-128 -128 256 256")

    triangle_attributes = {'points': '-128,-128 0,0 -128,128', 'fill': pattern.bg_color, 'stroke': pattern.bg_stroke}

    # Rotate the SVG
    if pattern.direction == Direction.TOP:
        triangle_attributes['transform'] = 'rotate(90, 0, 0)'
    elif pattern.direction == Direction.RIGHT:
        triangle_attributes['transform'] = 'rotate(180, 0, 0)'
    elif pattern.direction == Direction.BOTTOM:
        triangle_attributes['transform'] = 'rotate(270, 0, 0)'

    new_sub_element(svg, 'polygon', **triangle_attributes)

    # Path if it exists
    if pattern.path:
        path_attributes = {'d': pattern.path, 'fill': pattern.path_color, 'stroke': pattern.path_stroke}

        # Rotate the SVG
        if pattern.direction == Direction.TOP:
            path_attributes['transform'] = 'rotate(90, 0, 0)'
        elif pattern.direction == Direction.RIGHT:
            path_attributes['transform'] = 'rotate(180, 0, 0)'
        elif pattern.direction == Direction.BOTTOM:
            path_attributes['transform'] = 'rotate(270, 0, 0)'

        new_sub_element(svg, 'path', **path_attributes)

    return svg


def create_piece_svg(
        pattern_up: PatternSvgDefinition,
        pattern_right: PatternSvgDefinition,
        pattern_down: PatternSvgDefinition,
        pattern_left: PatternSvgDefinition
) -> _Element:
    # Create SVG root element
    svg = new_element('svg', xmlns="http://www.w3.org/2000/svg", version="1.1", width="256", height="256",
                      viewBox="-128 -128 256 256")

    # Create the four pattern SVGs
    svg_up = create_pattern_svg(pattern_up)
    svg_right = create_pattern_svg(pattern_right)
    svg_down = create_pattern_svg(pattern_down)
    svg_left = create_pattern_svg(pattern_left)

    # Add each SVG to the root SVG
    new_sub_element(svg, 'g').append(svg_up)
    new_sub_element(svg, 'g').append(svg_right)
    new_sub_element(svg, 'g').append(svg_down)
    new_sub_element(svg, 'g').append(svg_left)

    return svg


def merge_svg_into_one(svg_list: list,
                       view_box: tuple[int, int, int, int] = (0, 0, 256, 256),
                       width: int = 256,
                       height: int = 256) -> _Element:
    # Create SVG root element
    svg = new_element('svg', xmlns="http://www.w3.org/2000/svg", version="1.1", width=width, height=height,
                      viewBox=f"{view_box[0]} {view_box[1]} {view_box[2]} {view_box[3]}")

    # Add each SVG from the list
    for svg_element in svg_list:
        new_sub_element(svg, 'g').append(svg_element)

    # Draw a border around the SVG
    new_sub_element(svg, 'rect', x=view_box[0], y=view_box[1], width=view_box[2], height=view_box[3],
                    fill="none", stroke="black")

    return svg
