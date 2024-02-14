import random

import numpy as np

# Paramètres du plateau
size = 13  # Taille du plateau
number_of_symbols = 22  # Nombre de symboles différents


def generate_inner_symbols(size, number_of_symbols):
    vertical_symbols = np.random.randint(1, number_of_symbols, size=(size, size - 1))
    horizontal_symbols = np.random.randint(1, number_of_symbols, size=(size - 1, size))

    return vertical_symbols, horizontal_symbols


def create_board(size, number_of_symbols):
    board = [[None for _ in range(size)] for _ in range(size)]
    vertical_symbols, horizontal_symbols = generate_inner_symbols(size, number_of_symbols)

    for i in range(size):
        for j in range(size):
            top = "0000000000000000" if i == 0 else format(horizontal_symbols[i - 1, j], '016b')
            bottom = "0000000000000000" if i == size - 1 else format(horizontal_symbols[i, j], '016b')
            left = "0000000000000000" if j == 0 else format(vertical_symbols[i, j - 1], '016b')
            right = "0000000000000000" if j == size - 1 else format(vertical_symbols[i, j], '016b')
            board[i][j] = [top, right, bottom, left]

    return board


def print_board(board):
    for row in board:
        for piece in row:
            print(f"{', '.join(piece)}")


def format_board(board):
    formatted_board = f"{size}, {number_of_symbols}\n"
    for row in board:
        for piece in row:
            formatted_board += f"{', '.join(piece)}\n"
    return formatted_board


def shuffle_board(board):
    for row in board:
        for piece in row:
            for i in range(random.randint(0, 3)):
                piece.append(piece.pop(0))
    np.random.shuffle(board)
    return board


board = create_board(size, number_of_symbols)
print(print_board(board))
print(format_board(shuffle_board(board)))
