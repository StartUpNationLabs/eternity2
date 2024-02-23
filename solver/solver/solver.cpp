#include <algorithm>
#include <stack>
#include <random>
#include "solver.h"
#include "format/format.h"

auto rng = std::default_random_engine{};

std::vector<RotatedPiece>
possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, Index index) {
    // function to get the possible pieces that can be placed at the given position on the board
    // a piece is possible if it does not conflict with the pieces already on the board
    std::vector<RotatedPiece> possible;
    const auto x = index.first;
    const auto y = index.second;
    PiecePart top;
    PiecePart right;
    PiecePart bottom;
    PiecePart left;
    Piece mask = EMPTY;
    std::vector<Query> queries = {};
    if (x + 1 < board.size()) {
        right = get_piece_part(apply_rotation(board[y][x + 1]), LEFT_MASK);
        if (right != EMPTY) {
            mask |= RIGHT_MASK;
        }
        // if there is a piece to the right, There can't be a wall to the right
        // add a negative wall query to the queries that removes pieces with walls to the right
        queries.push_back({FULLWALL, RIGHT_MASK, QueryType::NEGATIVE});
    } else {
        right = WALL;
        mask |= RIGHT_MASK;
    }
    if (x >= 1) {
        left = get_piece_part(apply_rotation(board[y][x - 1]), RIGHT_MASK);
        if (left != EMPTY) {
            mask |= LEFT_MASK;
        }
        // if there is a piece to the left, There can't be a wall to the left
        // add a negative wall query to the queries that removes pieces with walls to the left
        queries.push_back({FULLWALL, LEFT_MASK, QueryType::NEGATIVE});
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
        queries.push_back({FULLWALL, DOWN_MASK, QueryType::NEGATIVE});
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
        queries.push_back({FULLWALL, UP_MASK, QueryType::NEGATIVE});
    } else {
        top = WALL;
        mask |= UP_MASK;
    }

    Piece piece = make_piece(top, right, bottom, left);
    log_piece(piece, "Query piece");
    const Query positive_query = {piece, mask, QueryType::POSITIVE};
    queries.push_back(positive_query);
    possible = match_piece_mask({queries}, pieces);
    return possible;
}


bool solve_board_recursive(Board &board, std::vector<PieceWAvailability> &pieces, Index index, int placed_pieces,
                           Board &max_board, int &max_count, std::mutex &mutex) {
    // function to solve the board recursively
    // the function tries to place a piece at the given position and then calls itself for the next position
    // if the board is solved, the function returns true
    log_board(board, format("Solving board at index: {}", index_to_string(index)));
    if (placed_pieces > max_count) {
        std::scoped_lock lock(mutex);
        max_count = placed_pieces;
        max_board = board;
    }
    if (is_end(board, index)) {
        return true;
    }


//    if (board[y][x].piece != EMPTY) {
//        return solve_board_recursive(board, pieces, x + 1, y, placed_pieces, max_board, max_count, mutex);
//    }

    auto possible = possible_pieces(board, pieces, index);
    // random for loop
    std::shuffle(possible.begin(), possible.end(), rng);
    // shuffle possible

    for (auto const &rotated_piece: possible) {
        place_piece(board, rotated_piece, index);
        // remove placed piece from pieces
        pieces[rotated_piece.index].available = false;
        Index next_index = get_next(board, index);
        if (solve_board_recursive(board, pieces, next_index, placed_pieces + 1, max_board, max_count, mutex)) {
            return true;
        }
        // add placed piece back to pieces
        pieces[rotated_piece.index].available = true;
#if SPDLOG_ACTIVE_LEVEL != SPDLOG_LEVEL_OFF
        log_board(board, format("Backtracking at index: {}", index_to_string(index)));
#endif
        remove_piece(board, index);
    }

    return false;

}

void solve_board(Board &board, const std::vector<Piece> &pieces, Board &max_board, int &max_count, std::mutex &mutex) {
    // function to solve the board
    // the function calls the recursive function to solve the board
    std::vector<PieceWAvailability> pieces_with_availability = create_pieces_with_availability(pieces);
    solve_board_recursive(board, pieces_with_availability, {0, 0}, 0, max_board, max_count, mutex);
}