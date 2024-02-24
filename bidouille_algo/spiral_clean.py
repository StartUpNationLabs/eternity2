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

    Parameters:
    matrix (list): 2D list representing the matrix.
    start_index (tuple): Tuple representing the starting index.

    Returns:
    list: List of next indices in 1D flattened format.
    """
    if not matrix:
        return []

    num_rows, num_cols = len(matrix), len(matrix[0])
    visited = [[False] * num_cols for _ in range(num_rows)]
    row_direction, col_direction = [0, 1, 0, -1], [1, 0, -1, 0]  # Direction vectors
    current_row, current_col = start_index[0], start_index[1]

    # Direction index: 0 - right, 1 - down, 2 - left, 3 - up
    direction_index = 0

    # Adjust the initial direction based on the start index
    if start_index == (0, num_cols - 1):
        direction_index = 1
    elif start_index == (num_rows - 1, 0):
        direction_index = 3
    elif start_index == (num_rows - 1, num_cols - 1):
        direction_index = 2

    next_indices_1d = [-1] * (num_rows * num_cols)  # Initialize with -1s to indicate the end
    last_index_1d = None
    for _ in range(num_rows * num_cols):
        curr_index_1d = convert_2d_to_1d(num_cols, (current_row, current_col))
        if last_index_1d is not None:
            next_indices_1d[last_index_1d] = curr_index_1d
        last_index_1d = curr_index_1d

        visited[current_row][current_col] = True
        next_row, next_col = current_row + row_direction[direction_index], current_col + col_direction[direction_index]
        if 0 <= next_row < num_rows and 0 <= next_col < num_cols and not visited[next_row][next_col]:
            current_row, current_col = next_row, next_col
        else:
            direction_index = (direction_index + 1) % 4
            current_row, current_col = current_row + row_direction[direction_index], current_col + col_direction[
                direction_index]

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
    main(3)
