//
// Created by appad on 10/02/2024.
//

#include "board.h"

#include "../format/format.h"
#include "spiral.h"

#include <algorithm>
#include <fstream>

auto create_board(int size) -> Board
{
    if (size <= 0)
    {
        // handle error
    }

    Board board = {std::vector<RotatedPiece>(size * size, {EMPTY, 0, 0}),
                   static_cast<size_t>(size),
                   std::vector<int>(size * size, 0)};

#ifdef SCAN_METHOD_SPIRAL
    board.next_index_cache = Spiral::spiral_order_from_board_size(size);
#elif defined(SCAN_METHOD_ROW)
    for (int i = 0; i < size * size; ++i)
    {
        board.next[i] = i + 1;
    }
    board.next[size * size - 1] = 0; // loop back to the start
#endif

    return board;
}

auto get_1d_board_index(const Board &board, Index index) -> size_t
{
    // function to get the 1D index of a 2D index
    return index.second * board.size + index.first;
}

auto get_2d_board_index(const Board &board, int index) -> Index
{
    // function to get the 2D index of a 1D index
    return {index % board.size, index / board.size};
}

void place_piece(Board &board, const RotatedPiece &piece, Index index)
{
    // function to place a piece on the board at the given position
    // the piece is rotated and placed on the board
    board.board[get_1d_board_index(board, index)] = piece;
}

void remove_piece(Board &board, Index index)
{
    // function to remove a piece from the board at the given position
    // the piece is replaced with an empty piece
    board.board[get_1d_board_index(board, index)] = {EMPTY, 0, 0};
}

auto get_next(const Board &board, Index index) -> Index
{
    // function to get the next position on the board
    // the function updates the index to the next position
    index.first++;
    if (index.first == board.size)
    {
        index.first = 0;
        index.second++;
    }
    return index;
}

auto is_end(const Board &board, Index index) -> bool
{
    // function to check if the index is at the end of the board
    return get_1d_board_index(board, index) == board.board.size();
}

auto index_to_string(Index index) -> std::string
{
    // function to convert the index to a string
    return format("x: {}, y: {}", index.first, index.second);
}

auto board_to_string(const Board &board) -> std::vector<std::string>
{
    // function to print the board to the console
    std::vector<std::string> board_lines;
    for (size_t y = 0; y < board.size; ++y)
    {
        std::vector<std::string> row_lines = piece_to_string(
            apply_rotation(board.board[get_1d_board_index(board, {0, y})]));
        for (size_t x = 1; x < board.size; ++x)
        {
            const auto &piece_lines = piece_to_string(
                apply_rotation(board.board[get_1d_board_index(board, {x, y})]));
            for (size_t j = 0; j < row_lines.size(); j++)
            {
                row_lines[j] += piece_lines[j];
            }
        }
        board_lines.insert(board_lines.end(), row_lines.begin(), row_lines.end());
    }
    return board_lines;
}

void log_board(const Board &board, const std::string &description)
{
#ifndef DISABLE_LOGGING
    // function to log the board to the console with std::cout
    std::cout << description << std::endl;
    for (auto const &line : board_to_string(board))
    {
        std::cout << line << std::endl;
    }
#endif
}

void export_board(const Board &board)
{
    // function to export the board to a csv file
    std::ofstream file("board.csv");

    for (const auto &piece : board.board)
    {
        file << csv_piece(piece) << '\n';
    }
}

auto export_board_to_csv_string(const Board &board) -> std::string
{
    // function to export the board to a csv string
    std::string csv_string;
    for (const auto &piece : board.board)
    {
        csv_string += csv_piece(piece) + "\n";
    }
    return csv_string;
}

auto get_neighbors(const Board &board, Index index) -> Neighbor
{
    // function to get the neighbors of a piece on the board
    // the function returns the pieces above, to the right, below, and to the left of the given piece
    Neighbor neighbor{};
    if (index.second > 0)
    {
        neighbor.up = &board.board[get_1d_board_index(board, {index.first, index.second - 1})];
    }
    else
    {
        neighbor.up = nullptr;
    }
    if (index.first < board.size - 1)
    {
        neighbor.right = &board.board[get_1d_board_index(board, {index.first + 1, index.second})];
    }
    else
    {
        neighbor.right = nullptr;
    }
    if (index.second < board.size - 1)
    {
        neighbor.down = &board.board[get_1d_board_index(board, {index.first, index.second + 1})];
    }
    else
    {
        neighbor.down = nullptr;
    }
    if (index.first > 0)
    {
        neighbor.left = &board.board[get_1d_board_index(board, {index.first - 1, index.second})];
    }
    else
    {
        neighbor.left = nullptr;
    }
    return neighbor;
}

auto get_piece(const Board &board, Index index) -> const RotatedPiece *
{
    // function to get the piece at the given position on the board
    return &board.board[get_1d_board_index(board, index)];
}