#include "solver.h"

#include "format/format.h"

#include <algorithm>
#include <random>
#include <stack>

auto rng = std::default_random_engine{};

auto possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, Index index)
    -> std::vector<RotatedPiece>
{
    // function to get the possible pieces that can be placed at the given position on the board
    // a piece is possible if it does not conflict with the pieces already on the board
    std::vector<RotatedPiece> possible;
    Neighbor neighbors         = get_neighbors(board, index);
    PiecePart top              = 0;
    PiecePart right            = 0;
    PiecePart bottom           = 0;
    PiecePart left             = 0;
    Piece mask                 = EMPTY;
    std::vector<Query> queries = {};
    if (neighbors.right != nullptr)
    {
        right = get_piece_part(apply_rotation(*neighbors.right), LEFT_MASK);
        if (right != EMPTY)
        {
            mask |= RIGHT_MASK;
        }
        // if there is a piece to the right, There can't be a wall to the right
        // add a negative wall query to the queries that removes pieces with walls to the right
        queries.emplace_back(FULLWALL, RIGHT_MASK, QueryType::NEGATIVE);
    }
    else
    {
        right = WALL;
        mask |= RIGHT_MASK;
    }
    if (neighbors.left != nullptr)
    {
        left = get_piece_part(apply_rotation(*neighbors.left), RIGHT_MASK);
        if (left != EMPTY)
        {
            mask |= LEFT_MASK;
        }
        // if there is a piece to the left, There can't be a wall to the left
        // add a negative wall query to the queries that removes pieces with walls to the left
        queries.emplace_back(FULLWALL, LEFT_MASK, QueryType::NEGATIVE);
    }
    else
    {
        left = WALL;
        mask |= LEFT_MASK;
    }

    if (neighbors.down != nullptr)
    {
        bottom = get_piece_part(apply_rotation(*neighbors.down), UP_MASK);
        if (bottom != EMPTY)
        {
            mask |= DOWN_MASK;
        }
        // if there is a piece below, There can't be a wall below
        // add a negative wall query to the queries that removes pieces with walls below
        queries.emplace_back(FULLWALL, DOWN_MASK, QueryType::NEGATIVE);
    }
    else
    {
        bottom = WALL;
        mask |= DOWN_MASK;
    }

    if (neighbors.up != nullptr)
    {
        top = get_piece_part(apply_rotation(*neighbors.up), DOWN_MASK);
        if (top != EMPTY)
        {
            mask |= UP_MASK;
        }
        // if there is a piece above, There can't be a wall above
        // add a negative wall query to the queries that removes pieces with walls above
        queries.emplace_back(FULLWALL, UP_MASK, QueryType::NEGATIVE);
    }
    else
    {
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

auto solve_board_recursive(Board &board,
                           std::vector<PieceWAvailability> &pieces,
                           Index index,
                           int placed_pieces,
                           SharedData &shared_data,
                           BoardHash &board_hash) -> bool
{
    // function to solve the board recursively
    // the function tries to place a piece at the given position and then calls itself for the next position
    // if the board is solved, the function returns true
    log_board(board, format("Solving board at index: {}", index_to_string(index)));
    shared_data.on_board_update(board);
    if (shared_data.stop)
    {
        return false;
    }
    // check if hash is already in the shared data if placed pieces is < HASH_THRESHOLD
    if (placed_pieces < shared_data.hash_length_threshold && shared_data.hashes.contains(board_hash))
    {
        shared_data.hash_hit_count++;
        return false;
    }

    if (placed_pieces > shared_data.max_count)
    {
        std::scoped_lock lock(shared_data.mutex);
        if (placed_pieces > shared_data.max_count)
        {
            shared_data.max_count = placed_pieces;
            shared_data.max_board = board;
        }
    }
    if (is_end(board, index))
    {
        return true;
    }

    std::vector<RotatedPiece> possible = {};

    const RotatedPiece *piece = get_piece(board, index);
    if (piece->index < 0)
    {
        possible.push_back(*piece);
    }
    else
    {
        possible = possible_pieces(board, pieces, index);
        // random for loop
        std::shuffle(possible.begin(), possible.end(), rng);
        // shuffle possible
    }

    for (auto const &rotated_piece : possible)
    {
        place_piece(board, rotated_piece, index);
        shared_data.pieces_placed++;
        // add placed piece to board hash
        if (placed_pieces < shared_data.hash_length_threshold)
        {
            board_hash += static_cast<char>(rotated_piece.index);
            board_hash += static_cast<char>(rotated_piece.rotation);
        }
        // remove placed piece from pieces
        pieces[rotated_piece.index].available = false;

        if (Index next_index = get_next(board, index);
            solve_board_recursive(board, pieces, next_index, placed_pieces + 1, shared_data, board_hash))
        {
            return true;
        }
        // copy board hash and insert it into the shared data
        if (placed_pieces < shared_data.hash_length_threshold)
        {
            std::scoped_lock lock(shared_data.mutex);
            shared_data.hashes.insert(board_hash);
        }
        // add placed piece back to pieces
        pieces[rotated_piece.index].available = true;
        // remove placed piece from board hash
        if (placed_pieces < shared_data.hash_length_threshold)
        {
            board_hash.pop_back();
            board_hash.pop_back();
        }
#if SPDLOG_ACTIVE_LEVEL != SPDLOG_LEVEL_OFF
        log_board(board, format("Backtracking at index: {}", index_to_string(index)));
#endif
        remove_piece(board, index);
        shared_data.on_board_update(board);
    }
    shared_data.board_count++;

    return false;
}

void solve_board(Board &board, const std::vector<Piece> &pieces, SharedData &shared_data)
{
    // function to solve the board
    // the function calls the recursive function to solve the board
    std::vector<PieceWAvailability> pieces_with_availability = create_pieces_with_availability(pieces);
    auto board_hash                                          = std::string();
    board_hash.reserve(board.size * board.size * 16);
    solve_board_recursive(board, pieces_with_availability, {0, 0}, 0, shared_data, board_hash);
    shared_data.stop = true;
}
