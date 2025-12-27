//
// Created by appad on 10/02/2024.
//

#include "board.h"
#include "../piece/piece.h"

#include "../format/format.h"
#include "scan_row.h"
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

    board.next_index_cache = Spiral::spiral_order_from_board_size(size);

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

auto get_next_using_cache(const Board &board, Index index) -> Index
{
    return get_2d_board_index(board, board.next_index_cache[get_1d_board_index(board, index)]);
}
auto get_next(const Board &board, Index index) -> Index
{
    return get_next_using_cache(board, index);
}

auto get_next_scan_row(const Board &board, Index index) -> Index
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
    return get_1d_board_index(board, index) == 2147483647;
}

auto index_to_string(Index index) -> std::string
{
    // function to convert the index to a string
    return eternity2::format("x: {}, y: {}", index.first, index.second);
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

auto binary_to_bucas_letter(uint16_t binary_value) -> char
{
    // Convert a 16-bit binary value to a BUCAS letter (a-w)
    // 0 or 65535 represent border/grey pieces -> 'a'
    // 1-22 represent different patterns -> 'b'-'w'
    if (binary_value == 0 || binary_value == 65535)
    {
        return 'a';
    }
    else if (binary_value >= 1 && binary_value <= 22)
    {
        return static_cast<char>('a' + binary_value);
    }
    else
    {
        throw std::runtime_error(eternity2::format("Invalid pattern value: {}", binary_value));
    }
}

auto extract_puzzle_name(const std::string &filepath) -> std::string
{
    // Extract the puzzle name from a file path
    // Example: "/path/to/size_7_colors_4_9e300d05.csv" -> "size_7_colors_4_9e300d05"

    // Find the last path separator (/ or \)
    size_t last_slash = filepath.find_last_of("/\\");
    std::string filename = (last_slash == std::string::npos) ? filepath : filepath.substr(last_slash + 1);

    // Find the last dot to remove extension
    size_t last_dot = filename.find_last_of('.');
    std::string name = (last_dot == std::string::npos) ? filename : filename.substr(0, last_dot);

    // Return the name, or default to "puzzle" if empty
    return name.empty() ? "puzzle" : name;
}

auto generate_bucas_url(const Board &board, const std::string &puzzle_name) -> std::string
{
    // Generate a BUCAS website URL from board data
    // Format: https://e2.bucas.name/#puzzle=NAME&board_w=W&board_h=H&board_edges=EDGES&motifs_order=jblackwood

    size_t board_w = board.size;
    size_t board_h = board.size;
    std::string board_edges;
    board_edges.reserve(board_w * board_h * 4); // 4 letters per piece

    // Iterate through all pieces in the board
    for (const auto &rotated_piece : board.board)
    {
        // Apply rotation to get the actual piece orientation
        Piece piece = apply_rotation(rotated_piece);

        // Extract 4x 16-bit segments from the 64-bit piece value
        // The piece is stored as 4 concatenated 16-bit values (top, right, bottom, left)
        std::bitset<64> bits(piece);

        // Extract each 16-bit segment
        uint16_t top    = static_cast<uint16_t>(std::bitset<16>(bits.to_string().substr(0, 16)).to_ulong());
        uint16_t right  = static_cast<uint16_t>(std::bitset<16>(bits.to_string().substr(16, 16)).to_ulong());
        uint16_t bottom = static_cast<uint16_t>(std::bitset<16>(bits.to_string().substr(32, 16)).to_ulong());
        uint16_t left   = static_cast<uint16_t>(std::bitset<16>(bits.to_string().substr(48, 16)).to_ulong());

        // Convert each edge to a BUCAS letter and append
        board_edges += binary_to_bucas_letter(top);
        board_edges += binary_to_bucas_letter(right);
        board_edges += binary_to_bucas_letter(bottom);
        board_edges += binary_to_bucas_letter(left);
    }

    // Build the complete BUCAS URL
    return eternity2::format("https://e2.bucas.name/#puzzle={}&board_w={}&board_h={}&board_edges={}&motifs_order=jblackwood",
                            puzzle_name, board_w, board_h, board_edges);
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

auto export_board_to_csv_string(const Board &board, const std::string &puzzle_name) -> std::string
{
    // function to export the board to a csv string with BUCAS URL on the first line
    std::string bucas_url = generate_bucas_url(board, puzzle_name);
    std::string csv_string = bucas_url + "\n";

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