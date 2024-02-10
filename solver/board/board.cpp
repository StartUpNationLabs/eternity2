//
// Created by appad on 10/02/2024.
//


#include "board.h"
#include "spdlog/spdlog.h"

Board create_board(int size) {
    // function to create an empty board with the given size and fill it with empty pieces
    // a board is a 2D array of pieces
    Board board(size, std::vector<RotatedPiece>(size, RotatedPiece()));
    return board;
}

void place_piece(Board board, const RotatedPiece &piece, int x, int y) {
    // function to place a piece on the board at the given position
    // the piece is rotated and placed on the board
    board[y][x] = piece;
}

void remove_piece(Board board, int x, int y) {
    // function to remove a piece from the board at the given position
    // the piece is replaced with an empty piece
    board[y][x] = RotatedPiece();
}

std::vector<RotatedPiece> possible_pieces(const Board &board, const std::vector<PIECE> &pieces, int x, int y) {
    // function to get the possible pieces that can be placed at the given position on the board
    // a piece is possible if it does not conflict with the pieces already on the board
    std::vector<RotatedPiece> possible;
    PIECE_PART top, right, bottom, left;
    PIECE mask = EMPTY;

    if (x + 1 < board.size()) {
        right = get_piece_part(board[y][x + 1].piece, LEFT_MASK);
        if (right != EMPTY) {
            mask |= LEFT_MASK;
        }
    } else {
        right = WALL;
        mask |= LEFT_MASK;
    }
    if (x - 1 >= 0) {
        left = get_piece_part(board[y][x - 1].piece, RIGHT_MASK);
        if (left != EMPTY) {
            mask |= RIGHT_MASK;
        }
    } else {
        left = WALL;
        mask |= RIGHT_MASK;
    }

    if (y + 1 < board.size()) {
        bottom = get_piece_part(board[y + 1][x].piece, UP_MASK);
        if (bottom != EMPTY) {
            mask |= UP_MASK;
        }
    } else {
        bottom = WALL;
        mask |= UP_MASK;
    }

    if (y - 1 >= 0) {
        top = get_piece_part(board[y - 1][x].piece, DOWN_MASK);
        if (top != EMPTY) {
            mask |= DOWN_MASK;
        }
    } else {
        top = WALL;
        mask |= DOWN_MASK;
    }

    PIECE piece = make_piece(top, right, bottom, left);
    const auto query = Query(piece, mask);
    possible = match_piece_mask({query}, pieces);
    return possible;
}


std::vector<std::string> board_to_string(const Board &board) {
    // function to print the board to the console
    std::vector<std::string> board_lines;
    for (const auto &row: board) {
        std::vector<std::string> row_lines = piece_to_string(row[0].piece);
        for (int i = 1; i < row.size(); i++) {
            const auto &piece = row[i].piece;
            const auto &piece_lines = piece_to_string(piece);
            for (int j = 0; j < row_lines.size(); j++) {
                row_lines[j] += piece_lines[j];
            }
        }
        board_lines.insert(board_lines.end(), row_lines.begin(), row_lines.end());
    }
    return board_lines;
}

void log_board(const Board &board, const std::string &description) {
    // function to log the board to the console
    spdlog::info(description);
    for (auto &line: board_to_string(board)) {
        spdlog::info(line);
    }
}