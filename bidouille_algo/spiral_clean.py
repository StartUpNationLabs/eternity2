def convert_1d_to_2d(board_size: int, index: int) -> tuple[int, int]:
    """
    Convert a 1D index to a 2D index.
    """
    return index // board_size, index % board_size


def convert_2d_to_1d(board_size: int, index: tuple[int, int]) -> int:
    """
    Convert a 2D index to a 1D index.
    """
    return index[0] * board_size + index[1]


def spiral_order(matrix, start_index):
    """
    Compute the spiral order starting from a given index and return the next index mapping in a 1D flattened format.
    """
    if not matrix:
        return []

    m, n = len(matrix), len(matrix[0])
    seen = [[False] * n for _ in range(m)]
    dr, dc = [0, 1, 0, -1], [1, 0, -1, 0]  # Direction vectors
    x, y, di = start_index[0], start_index[1], 0
    if start_index == (0, n - 1):
        di = 1
    elif start_index == (m - 1, 0):
        di = 3
    elif start_index == (m - 1, n - 1):
        di = 2

    next_indices_1d = [-1] * (m * n)  # Initialize with -1s to indicate the end
    last_index_1d = None
    for _ in range(m * n):
        curr_index_1d = convert_2d_to_1d(n, (x, y))
        if last_index_1d is not None:
            next_indices_1d[last_index_1d] = curr_index_1d
        last_index_1d = curr_index_1d

        seen[x][y] = True
        cr, cc = x + dr[di], y + dc[di]
        if 0 <= cr < m and 0 <= cc < n and not seen[cr][cc]:
            x, y = cr, cc
        else:
            di = (di + 1) % 4
            x, y = x + dr[di], y + dc[di]

    return next_indices_1d


def main(board_side_length: int = 3):
    matrix = [[j + i * board_side_length for j in range(board_side_length)] for i in range(board_side_length)]

    corners = [(0, 0), (0, board_side_length - 1), (board_side_length - 1, 0),
               (board_side_length - 1, board_side_length - 1)]
    combined_next_indices = []
    for corner in corners:
        next_indices = spiral_order(matrix, corner)
        combined_next_indices.extend(next_indices)

    # This combined_next_indices list now holds the 1D next indices starting from each corner in order
    print("Combined Next Indices:", combined_next_indices)


if __name__ == "__main__":
    main(2)
