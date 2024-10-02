//
// Created by appad on 29/02/2024.
//

#include "solvera.h"

#include "board/scan_utils.h"

#include <unifex/timed_single_thread_context.hpp>
unifex::timed_single_thread_context timer;
std::atomic<int> concurrent_jobs_count = 0;
int max_concurrent_jobs = 1;


auto build_response(const SharedData &shared_data, double elapsed_seconds) -> SolverRPC::Response
{
    auto end = std::chrono::system_clock::now();
    SolverRPC::Response response{};
    response.set_boards_analyzed(shared_data.board_count);
    response.set_hash_table_size(shared_data.hashes.size());
    response.set_time(elapsed_seconds);
    response.set_boards_per_second(static_cast<double>(shared_data.board_count) / elapsed_seconds);
    response.set_hashes_per_second(
        static_cast<double>(shared_data.hashes.size() - shared_data.redis_hash_count) / elapsed_seconds);
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
    spdlog::info("Response built");
    return response;
}

auto build_response_step_by_step(const Board &board, SharedData &data) -> SolverStepByStepRPC::Response
{
    SolverStepByStepRPC::Response response{};
    for (const auto &board_piece : board.board)
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
    // add max board
    for (const auto &board_piece : data.max_board.board)
    {
        auto *rotated_piece = response.add_max_board();
        rotated_piece->set_index(board_piece.index);
        rotated_piece->set_rotation(board_piece.rotation);
        auto *piece = rotated_piece->mutable_piece();
        piece->set_top(get_piece_part(board_piece.piece, UP_MASK));
        piece->set_right(get_piece_part(board_piece.piece, RIGHT_MASK));
        piece->set_bottom(get_piece_part(board_piece.piece, DOWN_MASK));
        piece->set_left(get_piece_part(board_piece.piece, LEFT_MASK));
    }
    // add stats
    auto elapsed_seconds = static_cast<double>(data.milliseconds_since_start) / 1000.0;
    response.set_boards_analyzed(data.board_count);
    response.set_time(elapsed_seconds);
    response.set_boards_per_second(static_cast<double>(data.board_count) / elapsed_seconds);
    response.set_steps(data.pieces_placed);
    return response;
}

auto load_board_pieces_from_request(const solver::v1::SolverSolveRequest &request)
    -> std::pair<Board, std::vector<Piece>>
{
    const auto &req_pieces = request.pieces();
    const auto size        = req_pieces.size();
    spdlog::info("Loading board and pieces from request");
    spdlog::info("Loaded {} pieces", size);
    Board board = create_board(static_cast<int>(sqrt(size)));
    std::vector<Piece> pieces;
    pieces.reserve(size * size);
    for (const auto &piece : req_pieces)
    {
        pieces.push_back(make_piece(piece.top(), piece.right(), piece.bottom(), piece.left()));
    }
    std::vector<int> candidate_path = {request.solve_path().begin(), request.solve_path().end()};
    if (check_path(candidate_path, board.size))
    {
        spdlog::info("Using custom solve path");
        board.next_index_cache = {request.solve_path().begin(), request.solve_path().end()};
        // log the solve path
        std::string solve_path = "Solve path: ";
        for (const auto &index : board.next_index_cache)
        {
            solve_path += std::to_string(index) + " ";
        }
        spdlog::info(solve_path);
    }
    else
    {
        spdlog::info("Using default solve path");
    }
    // add the hints pieces
    for (const auto &hint : request.hints())
    {
        spdlog::info("Placing hint piece");
        spdlog::info("Hint: x: {}, y: {}, rotation: {}", hint.x(), hint.y(), hint.rotation());
        auto index    = std::make_pair(hint.x(), hint.y());
        auto index_1d = get_1d_board_index(board, index);
        spdlog::info("Index 1d: {}", index_1d);
        if (hint.x() >= board.size || hint.y() >= board.size || index_1d >= pieces.size())
        {
            continue;
        }

        auto piece                 = request.pieces().at(static_cast<int>(index_1d));
        RotatedPiece rotated_piece = {make_piece(piece.top(), piece.right(), piece.bottom(), piece.left()),
                                      hint.rotation(),
                                      -static_cast<int>(index_1d)};
        place_piece(board, rotated_piece, index);
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

auto get_env_var(std::string const &key, std::string const &default_value) -> std::string
{
    char const *val = std::getenv(key.c_str());
    return val == nullptr ? default_value : std::string(val);
}

auto hash_pieces_board(const std::vector<Piece> &pieces, Board board) -> std::string
{
    std::string hash;
    for (const Piece &piece : pieces)
    {
        // zfill this bother piece is a ull
        hash += std::bitset<64>(piece).to_string();
    }
    for (const auto &next_index_cache : board.next_index_cache)
    {
        hash += std::bitset<64>(next_index_cache).to_string();
    }
    spdlog::info("Hash: {}", hash);
    return hash;
}

auto handle_server_solver_request(agrpc::GrpcContext &grpc_context,
                                  solver::v1::Solver::AsyncService &service1) -> unifex::any_sender_of<>
{
    return agrpc::register_sender_rpc_handler<SolverRPC>(
        grpc_context, service1, [&](SolverRPC &rpc, SolverRPC::Request &request) -> unifex::task<void> {
            spdlog::info("Received request");
            if (concurrent_jobs_count >= max_concurrent_jobs)
            {
                spdlog::info("Too many concurrent jobs");
                co_return;
            }
            concurrent_jobs_count++;
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
            spdlog::info("Hash length threshold: {}", request.hash_threshold());

            threads.reserve(thread_count);
            std::unordered_set<BoardHash> hashes = {};
            SharedData shared_data               = {max_board, max_count, mutex, hashes};
            shared_data.hash_length_threshold    = request.hash_threshold();
            auto start                           = std::chrono::high_resolution_clock::now();
            auto pieces_hash                     = hash_pieces_board(pieces, board);

            auto last_cache_pull = std::chrono::high_resolution_clock::now();
            if (request.use_cache())
            {
                spdlog::info("Using cache");
                last_cache_pull = std::chrono::high_resolution_clock::now();
            }
            spdlog::info("Starting solver", board.size);

            for (int i = 0; i < thread_count; i++)
            {
                threads.emplace_back(thread_function, board, pieces, std::ref(shared_data));
            }
            spdlog::info("Solver started");
            // every 2 seconds, print the current max count
            while (true)
            {
                co_await delay(std::chrono::milliseconds{request.wait_time()});
                double seconds_since_start = static_cast<double>(
                                                 std::chrono::duration_cast<std::chrono::milliseconds>(
                                                     std::chrono::high_resolution_clock::now() - start)
                                                     .count())
                                             / 1000.0;

                if (shared_data.max_count == board.size * board.size)
                {
                    spdlog::info("Found solution");
                    // stop threads
                    spdlog::info("Stopping threads");
                    concurrent_jobs_count--;
                    shared_data.stop = true;
                    for (auto &thread : threads)
                    {
                        // force stop
                        thread.join();
                    }
                    spdlog::info("Threads stopped");
                    co_await rpc.write(build_response(shared_data, seconds_since_start));
                    auto step_by_step = build_response_step_by_step(shared_data.max_board, shared_data);
                    std::string out   = std::string();
                    step_by_step.AppendToString(&out);

                    co_await rpc.finish(grpc::Status::OK);
                    co_return;
                }
                spdlog::info("Writing response");
                if (!co_await rpc.write(build_response(shared_data, seconds_since_start)))
                {
                    spdlog::info("Client cancelled request");
                    concurrent_jobs_count--;
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
                double seconds_since_last_cache_pull
                    = static_cast<double>(std::chrono::duration_cast<std::chrono::milliseconds>(
                                              std::chrono::high_resolution_clock::now() - last_cache_pull)
                                              .count())
                      / 1000.0;
                if (request.use_cache() && (seconds_since_last_cache_pull > request.cache_pull_interval()))
                {
                    last_cache_pull = std::chrono::high_resolution_clock::now();
                }
                spdlog::info("Response written");
            }
        });
}

auto handle_server_solver_request_step_by_step(agrpc::GrpcContext &grpc_context,
                                               solver::v1::Solver::AsyncService &service1)
    -> unifex::any_sender_of<>
{
    return agrpc::register_sender_rpc_handler<SolverStepByStepRPC>(
        grpc_context,
        service1,
        [&](SolverStepByStepRPC &rpc, SolverStepByStepRPC::Request &request) -> unifex::task<void> {
            spdlog::info("Received StepByStep request");
            auto [board, pieces] = load_board_pieces_from_request(request);
            std::mutex mutex;
            Board max_board = create_board(board.size);
            int max_count   = 0;
            std::unordered_set<BoardHash> hashes;
            SharedData shared_data = {max_board, max_count, mutex, hashes};
            std::vector<SolverStepByStepRPC::Response> responses;
            std::vector<SolverStepByStepRPC::Response> responses_to_send;
            shared_data.on_board_update = [&](const Board &board) {
                mutex.lock();
                auto res = build_response_step_by_step(board, shared_data);
                responses.push_back(res);
                mutex.unlock();
            };
            shared_data.hash_length_threshold = request.hash_threshold();
            spdlog::info("Starting solver with board size: {}", board.size);
            spdlog::info("Pieces: {}", pieces.size());
            spdlog::info("Timebetween: {}", request.wait_time());
            spdlog::info("Hash length threshold: {}", request.hash_threshold());
            auto start = std::chrono::high_resolution_clock::now();
            // launch the solver in a new thread
            std::thread solver_thread(thread_function, board, pieces, std::ref(shared_data));

            // while the solver is running, send the responses to the client
            while (!shared_data.stop)
            {
                co_await delay(std::chrono::milliseconds{request.wait_time()});
                const auto elapsed_milliseconds = std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::high_resolution_clock::now() - start);
                shared_data.milliseconds_since_start = elapsed_milliseconds.count();
                {
                    std::scoped_lock lock(mutex);
                    // only copy the last 10 responses
                    responses_to_send = {responses.end() - std::min(static_cast<int>(responses.size()), 10),
                                         responses.end()};
                    responses.clear();
                }
                for (auto const &res : responses_to_send)
                {
                    if (!co_await rpc.write(res))
                    {
                        spdlog::info("Client cancelled request");
                        shared_data.stop = true;
                        spdlog::info("Stopping solver thread");
                        solver_thread.join();
                        spdlog::info("Solver thread stopped");
                        co_await rpc.finish(grpc::Status::CANCELLED);
                        co_return;
                    }
                }
                responses_to_send.clear();
            }
            solver_thread.join();
            co_await rpc.finish(grpc::Status::OK);
            co_return;
        });
}
