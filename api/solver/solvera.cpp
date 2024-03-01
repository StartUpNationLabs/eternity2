//
// Created by appad on 29/02/2024.
//

#include <unifex/timed_single_thread_context.hpp>
#include "solvera.h"
SolverRPC::Response build_response(const SharedData &shared_data,
                                   double elapsed_seconds) {
    auto end = std::chrono::system_clock::now();
    SolverRPC::Response response{};
    response.set_boards_analyzed(shared_data.board_count);
    response.set_hash_table_size(shared_data.hashes.size());
    response.set_time(elapsed_seconds);
    response.set_boards_per_second((double ) shared_data.board_count / elapsed_seconds);
    response.set_hashes_per_second((double ) shared_data.hashes.size() / elapsed_seconds);
    response.set_hash_table_hits(shared_data.hash_hit_count);

    for (auto &board_piece: shared_data.max_board.board) {
        auto rotated_piece = response.add_rotated_pieces();
        rotated_piece->set_index(board_piece.index);
        rotated_piece->set_rotation(board_piece.rotation);
        auto piece = rotated_piece->mutable_piece();
        piece->set_top(get_piece_part(board_piece.piece, UP_MASK));
        piece->set_right(get_piece_part(board_piece.piece, RIGHT_MASK));
        piece->set_bottom(get_piece_part(board_piece.piece, DOWN_MASK));
        piece->set_left(get_piece_part(board_piece.piece, LEFT_MASK));
    }
    return response;
}
std::pair<Board, std::vector<Piece>> load_board_pieces_from_request(const SolverRPC::Request &request) {
    const auto &req_pieces = request.pieces();
    const auto size = req_pieces.size();
    Board board = create_board((int )sqrt(size));
    std::vector<Piece> pieces;
    pieces.reserve(size * size);
    for (const auto &piece: req_pieces) {
        pieces.push_back(
                make_piece(
                        piece.top(),
                        piece.right(),
                        piece.bottom(),
                        piece.left()
                )
        );
    }
    return std::make_pair(board, pieces);
}
void thread_function(Board board, std::vector<Piece> pieces, SharedData &shared_data) {
    solve_board(board, pieces, shared_data);
}

