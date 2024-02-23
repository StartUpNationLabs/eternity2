//
// Created by appad on 10/02/2024.
//


#include <fstream>
#include <algorithm>
#include "board.h"
#include "../format/format.h"


Board create_board(int size) {
    // function to create an empty board with the given size and fill it with empty pieces
    // a board is a 2D array of pieces
    Board board(size, std::vector<RotatedPiece>(size, {EMPTY, 0, 0}));
    return board;
}

void place_piece(Board &board, const RotatedPiece &piece, size_t x, size_t y) {
    // function to place a piece on the board at the given position
    // the piece is rotated and placed on the board
    board[y][x] = piece;
}

void remove_piece(Board &board, size_t x, size_t y) {
    // function to remove a piece from the board at the given position
    // the piece is replaced with an empty piece
    board[y][x] = {EMPTY, 0, 0};
}


std::vector<std::string> board_to_string(const Board &board) {
    // function to print the board to the console
    std::vector<std::string> board_lines;
    for (const auto &row: board) {
        std::vector<std::string> row_lines = piece_to_string(rotate_piece_right(row[0].piece, row[0].rotation));
        for (size_t i = 1; i < row.size(); i++) {
            const auto &piece = row[i].piece;
            const auto &piece_lines = piece_to_string(rotate_piece_right(piece, row[i].rotation));
            for (size_t j = 0; j < row_lines.size(); j++) {
                row_lines[j] += piece_lines[j];
            }
        }
        board_lines.insert(board_lines.end(), row_lines.begin(), row_lines.end());
    }
    return board_lines;
}

void log_board(const Board &board, const std::string &description) {
#ifndef DISABLE_LOGGING
    // function to log the board to the console with std::cout
    std::cout << description << std::endl;
    for (auto const &line: board_to_string(board)) {
        std::cout << line << std::endl;
    }
#endif
}


void export_board(const Board &board) {
    // function to export the board to a csv file
    std::ofstream file("board.csv");

    for (const auto &row: board) {
        for (const auto &piece: row) {
            file << csv_piece(piece) << std::endl;
        }
    }
}

std::string export_board_to_csv_string(const Board &board) {
    // function to export the board to a csv string
    std::string csv_string;
    for (const auto &row: board) {
        for (const auto &piece: row) {
            csv_string += csv_piece(piece) + "\n";
        }
    }
    return csv_string;
}


unsigned long long int hash_board(const Board &board) {
    // function to hash the board
    // the function uses the hash of the pieces on the board to create a unique hash for the board
    unsigned long long int hash = 0;
    for (const auto &row: board) {
        for (const auto &piece: row) {
            hash = hash * 31 + (piece.index + piece.rotation);
        }
    }
    return hash;
}