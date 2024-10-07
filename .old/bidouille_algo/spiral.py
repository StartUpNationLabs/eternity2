"""
We consider the following 1D array :
[0, 1, 2, 3, 4, 5, 6, 7, 8]

That fills the following 2D array :
[[0, 1, 2],
 [3, 4, 5],
 [6, 7, 8]]

The spiral should go through the array in the following order :
0 -> 1 -> 2 -> 5 -> 8 -> 7 -> 6 -> 3 -> 4
"""


def convert_1d_to_2d(board_size: int, index: int) -> tuple[int, int]:
    """
    Method that convert a 1D index to a 2D index
    """
    return index // board_size, index % board_size


def convert_2d_to_1d(board_size: int, index: tuple[int, int]) -> int:
    """
    Method that convert a 2D index to a 1D index
    """
    return index[0] * board_size + index[1]


def spiral_order(matrix, start_index):
    # print("Start index: ", start_index)

    ans = []
    next_index = {}

    if len(matrix) == 0:
        return ans, next_index

    m = len(matrix)
    n = len(matrix[0])
    seen = [[0 for _ in range(n)] for _ in range(m)]
    dr = [0, 1, 0, -1]
    dc = [1, 0, -1, 0]

    # Determine the starting point and direction based on the start_index
    if start_index == (0, 0):  # top-left corner
        x, y, di = 0, 0, 0
    elif start_index == (0, n - 1):  # top-right corner
        x, y, di = 0, n - 1, 1
    elif start_index == (m - 1, 0):  # bottom-left corner
        x, y, di = m - 1, 0, 3
    else:  # bottom-right corner
        x, y, di = m - 1, n - 1, 2

    # Iterate from 0 to R * C - 1
    for _ in range(m * n):
        if ans:
            next_index[ans[-1]] = (x, y)
        ans.append((x, y))
        seen[x][y] = True
        cr = x + dr[di]
        cc = y + dc[di]

        if 0 <= cr < m and 0 <= cc < n and not (seen[cr][cc]):
            x = cr
            y = cc
        else:
            di = (di + 1) % 4
            x += dr[di]
            y += dc[di]
    return ans, next_index


def store_all_next(matrix, starting_coordinate: tuple[int, int]) -> dict[int, int]:
    # Get the spiral order and the next index
    spiral, next_index_2d = spiral_order(matrix, starting_coordinate)
    # print("Spiral: ", spiral)
    # print("Next index 2D: ", next_index_2d)

    # Convert the 2D keys and the 2D values to 1D
    next_index = {}
    for key, value in next_index_2d.items():
        next_index[convert_2d_to_1d(len(matrix), key)] = convert_2d_to_1d(len(matrix), value)

    for i in range(len(spiral)):
        if i not in next_index.keys():
            next_index[i] = -1

    # print("Next index: ", next_index)

    return next_index


def print_next(next, text: str):
    print(f"=== {text} ===")
    for i in range(len(next)):
        print("Index: ", i, " Next index: ", next[i])


def display_all_next(top_left_next, top_right_next, bottom_left_next, bottom_right_next):
    print_next(top_left_next, "Top left next")
    print_next(top_right_next, "Top right next")
    print_next(bottom_left_next, "Bottom left next")
    print_next(bottom_right_next, "Bottom right next")


def main(board_side_length: int = 3):
    table = [i for i in range(board_side_length ** 2)]
    matrix = [[table[i * board_side_length + j] for j in range(board_side_length)] for i in range(board_side_length)]

    # From the top-left corner
    # print("============================")
    # print("Top left corner")
    top_left_next: dict[int, int] = store_all_next(matrix, (0, 0))
    # From the top-right corner
    # print("============================")
    # print("Top right corner")
    top_right_next: dict[int, int] = store_all_next(matrix, (0, board_side_length - 1))
    # From the bottom-left corner
    # print("============================")
    # print("Bottom left corner")
    bottom_left_next: dict[int, int] = store_all_next(matrix, (board_side_length - 1, 0))
    # From the bottom-right corner
    # print("============================")
    # print("Bottom right corner")
    bottom_right_next: dict[int, int] = store_all_next(matrix, (board_side_length - 1, board_side_length - 1))
    # print("============================")

    debug: bool = False
    if debug:
        display_all_next(top_left_next, top_right_next, bottom_left_next, bottom_right_next)

    # Create next_index list that contains only the next index
    # TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT
    next_index = []

    for i in range(len(top_left_next)):
        next_index.append(top_left_next[i])

    for i in range(len(top_right_next)):
        next_index.append(top_right_next[i])

    for i in range(len(bottom_left_next)):
        next_index.append(bottom_left_next[i])

    for i in range(len(bottom_right_next)):
        next_index.append(bottom_right_next[i])

    # Print the next index
    print_next(next_index, "Next index")


if __name__ == "__main__":
    main(3)
