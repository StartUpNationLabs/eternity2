#include "solver_v0.h"
#include "v1/piece_search/piece_search.h"
#include <algorithm>
#include <random>

namespace eternity2_v0 {

// Bring common types into this namespace
using eternity2_common::PiecePart;
using eternity2_common::Piece;
using eternity2_common::EMPTY;
using eternity2_common::WALL;
using eternity2_common::UP_MASK;
using eternity2_common::RIGHT_MASK;
using eternity2_common::DOWN_MASK;
using eternity2_common::LEFT_MASK;
using eternity2_common::FULLWALL;
using eternity2_common::make_piece;
using eternity2_common::get_piece_part;

static thread_local std::default_random_engine rng;

// Helper function to get possible pieces for a position (v0 algorithm)
static std::vector<RotatedPiece> possible_pieces(
    const Board& board,
    const std::vector<PieceWAvailability>& pieces,
    Index index)
{
    std::vector<RotatedPiece> possible;
    Neighbor neighbors = get_neighbors(board, index);

    PiecePart top = 0, right = 0, bottom = 0, left = 0;
    Piece mask = EMPTY;
    std::vector<Query> queries;

    // Right neighbor
    if (neighbors.right != nullptr) {
        right = get_piece_part(apply_rotation(*neighbors.right), LEFT_MASK);
        if (right != EMPTY) {
            mask |= RIGHT_MASK;
        }
        queries.push_back({FULLWALL, RIGHT_MASK, QueryType::NEGATIVE});
    } else {
        right = WALL;
        mask |= RIGHT_MASK;
    }

    // Left neighbor
    if (neighbors.left != nullptr) {
        left = get_piece_part(apply_rotation(*neighbors.left), RIGHT_MASK);
        if (left != EMPTY) {
            mask |= LEFT_MASK;
        }
        queries.push_back({FULLWALL, LEFT_MASK, QueryType::NEGATIVE});
    } else {
        left = WALL;
        mask |= LEFT_MASK;
    }

    // Down neighbor
    if (neighbors.down != nullptr) {
        bottom = get_piece_part(apply_rotation(*neighbors.down), UP_MASK);
        if (bottom != EMPTY) {
            mask |= DOWN_MASK;
        }
        queries.push_back({FULLWALL, DOWN_MASK, QueryType::NEGATIVE});
    } else {
        bottom = WALL;
        mask |= DOWN_MASK;
    }

    // Up neighbor
    if (neighbors.up != nullptr) {
        top = get_piece_part(apply_rotation(*neighbors.up), DOWN_MASK);
        if (top != EMPTY) {
            mask |= UP_MASK;
        }
        queries.push_back({FULLWALL, UP_MASK, QueryType::NEGATIVE});
    } else {
        top = WALL;
        mask |= UP_MASK;
    }

    Piece piece = make_piece(top, right, bottom, left);
    queries.push_back({piece, mask, QueryType::POSITIVE});
    possible = match_piece_mask({queries}, pieces);

    return possible;
}

// Recursive backtracking solver (v0 algorithm)
static bool solve_board_recursive(
    Board& board,
    std::vector<PieceWAvailability>& pieces,
    Index index,
    int placed_pieces,
    SharedDataV0& shared_data,
    std::string& board_hash)
{
    if (shared_data.stop) {
        return false;
    }

    // Hash-based pruning
    if (placed_pieces < static_cast<int>(shared_data.hash_length_threshold) &&
        shared_data.hashes.find(board_hash) != shared_data.hashes.end()) {
        shared_data.hash_hit_count++;
        return false;
    }

    // Update maximum progress
    if (placed_pieces > shared_data.max_count) {
        std::scoped_lock lock(shared_data.mutex);
        if (placed_pieces > shared_data.max_count) {
            shared_data.max_count = placed_pieces;
            shared_data.max_board = board;
        }
    }

    // Check if solved
    if (is_end(board, index)) {
        return true;
    }

    std::vector<RotatedPiece> possible;
    const RotatedPiece* piece = get_piece(board, index);

    // If piece already placed (pre-filled), continue to next
    if (piece->index < 0) {
        auto rotated_piece = *piece;
        shared_data.pieces_placed++;

        if (placed_pieces < static_cast<int>(shared_data.hash_length_threshold)) {
            board_hash += static_cast<char>(rotated_piece.index);
            board_hash += static_cast<char>(rotated_piece.rotation);
        }

        Index next_index = get_next(board, index);
        if (solve_board_recursive(board, pieces, next_index, placed_pieces + 1, shared_data, board_hash)) {
            return true;
        }

        if (placed_pieces < static_cast<int>(shared_data.hash_length_threshold)) {
            board_hash.pop_back();
            board_hash.pop_back();
        }

        shared_data.board_count++;
        return false;
    }

    // Get possible pieces and randomize (v0 characteristic)
    possible = possible_pieces(board, pieces, index);
    std::shuffle(possible.begin(), possible.end(), rng);

    // Try each possible piece
    for (const auto& rotated_piece : possible) {
        place_piece(board, rotated_piece, index);
        shared_data.pieces_placed++;

        // Update board hash
        if (placed_pieces < static_cast<int>(shared_data.hash_length_threshold)) {
            board_hash += static_cast<char>(rotated_piece.index);
            board_hash += static_cast<char>(rotated_piece.rotation);
        }

        // Mark piece as used
        pieces[rotated_piece.index].available = false;

        // Recurse
        Index next_index = get_next(board, index);
        if (solve_board_recursive(board, pieces, next_index, placed_pieces + 1, shared_data, board_hash)) {
            return true;
        }

        // Backtrack: store hash
        if (placed_pieces < static_cast<int>(shared_data.hash_length_threshold)) {
            std::scoped_lock lock(shared_data.mutex);
            shared_data.hashes.insert(board_hash);
        }

        // Restore state
        pieces[rotated_piece.index].available = true;

        if (placed_pieces < static_cast<int>(shared_data.hash_length_threshold)) {
            board_hash.pop_back();
            board_hash.pop_back();
        }

        remove_piece(board, index);
    }

    shared_data.board_count++;
    return false;
}

void solve_board(Board& board, const std::vector<Piece>& pieces, SharedDataV0& shared_data) {
    std::vector<PieceWAvailability> pieces_with_availability = create_pieces_with_availability(pieces);
    std::string board_hash;
    board_hash.reserve(board.size * board.size * 16);

    solve_board_recursive(board, pieces_with_availability, {0, 0}, 0, shared_data, board_hash);
    shared_data.stop = true;
}

} // namespace eternity2_v0
