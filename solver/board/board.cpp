//
// Created by appad on 10/02/2024.
//


#include <stack>
#include <random>
#include <fstream>
#include "board.h"
#include "spdlog/spdlog.h"
auto rng = std::default_random_engine {};

Board create_board(int size) {
    // function to create an empty board with the given size and fill it with empty pieces
    // a board is a 2D array of pieces
    Board board(size, std::vector<RotatedPiece>(size, RotatedPiece()));
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
    board[y][x] = RotatedPiece();
}

std::vector<RotatedPiece>
possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, size_t x, size_t y) {
    // function to get the possible pieces that can be placed at the given position on the board
    // a piece is possible if it does not conflict with the pieces already on the board
    std::vector<RotatedPiece> possible;
    PIECE_PART top;
    PIECE_PART right;
    PIECE_PART bottom;
    PIECE_PART left;
    PIECE mask = EMPTY;
    std::vector<Query> queries = {};
    if (x + 1 < board.size()) {
        right = get_piece_part(apply_rotation(board[y][x + 1]), LEFT_MASK);
        if (right != EMPTY) {
            mask |= RIGHT_MASK;
        }
        // if there is a piece to the right, There can't be a wall to the right
        // add a negative wall query to the queries that removes pieces with walls to the right
        queries.push_back(Query(FULLWALL, RIGHT_MASK, QueryType::NEGATIVE));
    } else {
        right = WALL;
        mask |= RIGHT_MASK;
    }
    if ((x) >= 1) {
        left = get_piece_part(apply_rotation(board[y][x - 1]), RIGHT_MASK);
        if (left != EMPTY) {
            mask |= LEFT_MASK;
        }
        // if there is a piece to the left, There can't be a wall to the left
        // add a negative wall query to the queries that removes pieces with walls to the left
        queries.push_back(Query(FULLWALL, LEFT_MASK, QueryType::NEGATIVE));
    } else {
        left = WALL;
        mask |= LEFT_MASK;
    }

    if (y + 1 < board.size()) {
        bottom = get_piece_part(apply_rotation(board[y + 1][x]), UP_MASK);
        if (bottom != EMPTY) {
            mask |= DOWN_MASK;
        }
        // if there is a piece below, There can't be a wall below
        // add a negative wall query to the queries that removes pieces with walls below
        queries.push_back(Query(FULLWALL, DOWN_MASK, QueryType::NEGATIVE));
    } else {
        bottom = WALL;
        mask |= DOWN_MASK;
    }

    if (y >= 1) {
        top = get_piece_part(apply_rotation(board[y - 1][x]), DOWN_MASK);
        if (top != EMPTY) {
            mask |= UP_MASK;
        }
        // if there is a piece above, There can't be a wall above
        // add a negative wall query to the queries that removes pieces with walls above
        queries.push_back(Query(FULLWALL, UP_MASK, QueryType::NEGATIVE));
    } else {
        top = WALL;
        mask |= UP_MASK;
    }

    PIECE piece = make_piece(top, right, bottom, left);
    log_piece(piece, "Query piece");
    const auto positive_query = Query(piece, mask);
    queries.push_back(positive_query);
    possible = match_piece_mask({queries}, pieces);
    return possible;
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
#if SPDLOG_ACTIVE_LEVEL != SPDLOG_LEVEL_OFF
    // function to log the board to the console
    spdlog::info(description);
    for (auto const &line: board_to_string(board)) {
        spdlog::info(line);
    }
#endif
}

bool solve_board_recursive(Board &board, std::vector<PieceWAvailability> &pieces, size_t x, size_t y, int placed_pieces,
                           Board &max_board, int &max_count, std::mutex &mutex) {
    // function to solve the board recursively
    // the function tries to place a piece at the given position and then calls itself for the next position
    // if the board is solved, the function returns true
    log_board(board, fmt::format("Solving board at x: {}, y: {}", x, y));
    if (placed_pieces > max_count) {
        std::scoped_lock lock(mutex);
        max_count = placed_pieces;
        max_board = board;
    }


    if (x == board.size()) {
        x = 0;
        y++;
    }
    if (y == board.size()) {
        return true;
    }
//    if (board[y][x].piece != EMPTY) {
//        return solve_board_recursive(board, pieces, x + 1, y, placed_pieces, max_board, max_count, mutex);
//    }

    auto possible = possible_pieces(board, pieces, x, y);
    // random for loop
    std::shuffle(possible.begin(), possible.end(), rng);
    // shuffle possible

    for (auto const &rotated_piece: possible) {
        place_piece(board, rotated_piece, x, y);
        // remove placed piece from pieces
        pieces[rotated_piece.index].available = false;

        if (solve_board_recursive(board, pieces, x + 1, y, placed_pieces + 1, max_board, max_count, mutex)) {
            return true;
        }
        // add placed piece back to pieces
        pieces[rotated_piece.index].available = true;
        SPDLOG_INFO("Backtracking");
        remove_piece(board, x, y);
    }

    return false;

}

void solve_board_iterative(Board &board, std::vector<PieceWAvailability> &pieces) {
    // function to solve the board iteratively
    // the function uses a stack to keep track of the positions and pieces to try
    std::stack<std::tuple<size_t, size_t, size_t>> stack; // x, y, possible_piece_index
    stack.emplace(0, 0, 0);
    while (!stack.empty()) {
        auto [x, y, possible_piece_index] = stack.top();
        if (y == board.size()) {
            break;
        }
        if (x == board.size()) {
            stack.emplace(0, y + 1, 0);
            continue;
        }
        if (board[y][x].piece != EMPTY) {
            stack.emplace(x + 1, y, 0);
            continue;
        }
        auto possible = possible_pieces(board, pieces, x, y);
        if (possible_piece_index < possible.size()) {
            auto const &rotated_piece = possible[possible_piece_index];
            place_piece(board, rotated_piece, x, y);
            // remove placed piece from pieces
            pieces[rotated_piece.index].available = false;
            stack.emplace(x + 1, y, 0);
        } else {
            if (stack.empty()) {
                break;
            }
            stack.pop();
            auto [last_x, last_y, last_possible_piece_index] = stack.top();
            remove_piece(board, last_x, last_y);
            pieces[board[last_y][last_x].index].available = true;
            stack.pop();
            stack.emplace(last_x, last_y, last_possible_piece_index + 1);
        }


    }
}

void solve_board(Board &board, const std::vector<PIECE> &pieces, Board &max_board, int &max_count, std::mutex &mutex) {
    // function to solve the board
    // the function calls the recursive function to solve the board
    std::vector<PieceWAvailability> pieces_with_availability = create_pieces_with_availability(pieces);
//    solve_board_iterative(board, pieces_with_availability);
    solve_board_recursive(board, pieces_with_availability, 0, 0, 0, max_board, max_count, mutex);
}

void export_board(const Board &board) {
    // function to export the board to a csv file
    std::ofstream file("board.csv");

    for (const auto &row: board) {
        for (const auto &piece: row) {
            file << csv_piece(piece.piece) << std::endl;
        }
    }
}
