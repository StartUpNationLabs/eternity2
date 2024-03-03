//
// Created by appad on 29/02/2024.
//

#include "solvera.h"

#include <unifex/timed_single_thread_context.hpp>
unifex::timed_single_thread_context timer;

auto build_response(const SharedData &shared_data, double elapsed_seconds) -> SolverRPC::Response
{
    auto end = std::chrono::system_clock::now();
    SolverRPC::Response response{};
    response.set_boards_analyzed(shared_data.board_count);
    response.set_hash_table_size(shared_data.hashes.size());
    response.set_time(elapsed_seconds);
    response.set_boards_per_second(static_cast<double>(shared_data.board_count) / elapsed_seconds);
    response.set_hashes_per_second(static_cast<double>(shared_data.hashes.size()) / elapsed_seconds);
    response.set_hash_table_hits(shared_data.hash_hit_count);

    for (auto &board_piece : shared_data.max_board.board)
    {
        auto *rotated_piece = response.add_rotated_pieces();
        rotated_piece->set_index(board_piece.index);
        rotated_piece->set_rotation(board_piece.rotation);
        auto *piece = rotated_piece->mutable_piece();
        piece->set_top(get_piece_part(board_piece.piece, UP_MASK));
        piece->set_right(get_piece_part(board_piece.piece, RIGHT_MASK));
        piece->set_bottom(get_piece_part(board_piece.piece, DOWN_MASK));
        piece->set_left(get_piece_part(board_piece.piece, LEFT_MASK));
    }
    return response;
}
auto load_board_pieces_from_request(const SolverRPC::Request &request) -> std::pair<Board, std::vector<Piece>>
{
    const auto &req_pieces = request.pieces();
    const auto size        = req_pieces.size();
    Board board            = create_board(static_cast<int>(sqrt(size)));
    std::vector<Piece> pieces;
    pieces.reserve(size * size);
    for (const auto &piece : req_pieces)
    {
        pieces.push_back(make_piece(piece.top(), piece.right(), piece.bottom(), piece.left()));
    }
    return std::make_pair(board, pieces);
}
void thread_function(Board board, std::vector<Piece> pieces, SharedData &shared_data)
{
    solve_board(board, pieces, shared_data);
}
auto delay(std::chrono::milliseconds ms) -> unifex::_timed_single_thread_context::_schedule_after_sender<
    std::chrono::duration<long, std::ratio<1, 1000>>>::type
{
    return unifex::schedule_after(timer.get_scheduler(), ms);
}
auto handle_server_solver_request(agrpc::GrpcContext &grpc_context,
                                  solver::v1::Solver::AsyncService &service1) -> unifex::any_sender_of<>
{
    return agrpc::register_sender_rpc_handler<SolverRPC>(
        grpc_context, service1, [&](SolverRPC &rpc, SolverRPC::Request &request) -> unifex::task<void> {
            spdlog::info("Received request");
            auto [board, pieces] = load_board_pieces_from_request(request);
            std::mutex mutex;
            Board max_board = create_board(board.size);
            int max_count   = 0;
            std::vector<std::thread> threads;
            int max_thread_count = std::max(4, static_cast<int>(std::thread::hardware_concurrency()));
            int thread_count     = std::min(max_thread_count, static_cast<int>(request.threads()));
            spdlog::info("Starting solver with board size: {}", board.size);
            spdlog::info("Using {} threads", thread_count);
            spdlog::info("Pieces: {}", pieces.size());
            spdlog::info("Timebetween: {}", request.wait_time());
            threads.reserve(thread_count);
            std::unordered_set<BoardHash> hashes;
            SharedData shared_data = {max_board, max_count, mutex, hashes};
            auto start             = std::chrono::high_resolution_clock::now();
            for (int i = 0; i < thread_count; i++)
            {
                threads.emplace_back(thread_function, board, pieces, std::ref(shared_data));
            }

            // every 2 seconds, print the current max count
            while (true)
            {
                co_await delay(std::chrono::milliseconds{request.wait_time()});

                double seconds_since_start = static_cast<double>(
                                                 std::chrono::duration_cast<std::chrono::milliseconds>(
                                                     std::chrono::high_resolution_clock::now() - start)
                                                     .count())
                                             / 1000.0;
                if (max_count == board.size * board.size)
                {
                    spdlog::info("Found solution");
                    co_await rpc.write(build_response(shared_data, seconds_since_start));
                    // stop threads
                    spdlog::info("Stopping threads");
                    shared_data.stop = true;
                    for (auto &thread : threads)
                    {
                        // force stop
                        thread.join();
                    }
                    spdlog::info("Threads stopped");
                    co_await rpc.finish(grpc::Status::OK);
                    co_return;
                }

                if (!co_await rpc.write(build_response(shared_data, seconds_since_start)))
                {
                    spdlog::info("Client cancelled request");
                    spdlog::info("Stopping threads");
                    // stop threads
                    shared_data.stop = true;
                    for (auto &thread : threads)
                    {
                        // force stop
                        thread.join();
                    }
                    spdlog::info("Threads stopped");
                    co_await rpc.finish(grpc::Status::CANCELLED);
                    co_return;
                }
            }
        });
}
