//
// Created by appad on 29/02/2024.
//

#include "solvera.h"

#include <sw/redis++/redis++.h>
#include <unifex/timed_single_thread_context.hpp>
unifex::timed_single_thread_context timer;
void update_cache(std::mutex &mutex,
                  const std::string &pieces_hash,
                  sw::redis::Redis &redis,
                  SharedData &shared_data)
{
    std::scoped_lock lock(mutex);
    auto temp = std::unordered_set<BoardHash>{};
    redis.smembers(pieces_hash, std::inserter(temp, temp.end()));
    // copy the temp set into the shared data
    for (const auto &hash : temp)
    {
        shared_data.hashes.insert(hash);
    }
    shared_data.redis_hash_count = temp.size();
    spdlog::info("Loaded {} hashes from redis", shared_data.redis_hash_count);
}

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
    return response;
}

auto build_response_step_by_step(const Board &board) -> SolverStepByStepRPC::Response
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
    return response;
}

auto load_board_pieces_from_request(const solver::v1::SolverSolveRequest &request)
    -> std::pair<Board, std::vector<Piece>>
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

auto get_env_var(std::string const &key, std::string const &default_value) -> std::string
{
    char const *val = std::getenv(key.c_str());
    return val == nullptr ? default_value : std::string(val);
}

auto hash_pieces(const std::vector<Piece> &pieces) -> std::string
{
    std::string hash;
    for (const Piece &piece : pieces)
    {
        // zfill this bother piece is a ull
        hash += std::bitset<64>(piece).to_string();
    }
    return hash;
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
            spdlog::info("Hash length threshold: {}", request.hash_threshold());

            threads.reserve(thread_count);
            std::unordered_set<BoardHash> hashes = {};
            SharedData shared_data               = {max_board, max_count, mutex, hashes};
            shared_data.hash_length_threshold    = request.hash_threshold();
            auto start                           = std::chrono::high_resolution_clock::now();
            auto pieces_hash                     = hash_pieces(pieces);
            // load hashes from redis if they exist

            sw::redis::ConnectionOptions connection_options;
            connection_options.host = get_env_var("REDIS_HOST", "localhost");
            connection_options.port = static_cast<int>(
                strtol(get_env_var("REDIS_PORT", "6379").c_str(), nullptr, 10));
            connection_options.password = get_env_var("REDIS_PASSWORD", "");
            connection_options.db       = 0;
            sw::redis::Redis redis      = sw::redis::Redis(connection_options);

            // check if connection is working
            try
            {
                redis.ping();
            }
            catch (const sw::redis::Error &e)
            {
                spdlog::error("Could not connect to redis: {}", e.what());
                co_return;
            }
            auto last_cache_pull = std::chrono::high_resolution_clock::now();
            if (request.use_cache())
            {
                update_cache(mutex, pieces_hash, redis, shared_data);
                last_cache_pull = std::chrono::high_resolution_clock::now();
            }

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

                double seconds_since_last_cache_pull
                    = static_cast<double>(std::chrono::duration_cast<std::chrono::milliseconds>(
                                              std::chrono::high_resolution_clock::now() - last_cache_pull)
                                              .count())
                      / 1000.0;
                if (request.use_cache() && (seconds_since_last_cache_pull > request.cache_pull_interval()))
                {
                    update_cache(mutex, pieces_hash, redis, shared_data);
                    last_cache_pull = std::chrono::high_resolution_clock::now();
                }

                if (max_count == board.size * board.size)
                {
                    spdlog::info("Found solution");
                    co_await rpc.write(build_response(shared_data, seconds_since_start));
                    auto step_by_step = build_response_step_by_step(shared_data.max_board);
                    std::string out   = std::string();
                    step_by_step.AppendToString(&out);

                    redis.sadd("solutions_" + pieces_hash, out);

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
                //  insert into redis
                redis.sadd(pieces_hash, shared_data.hashes.begin(), shared_data.hashes.end());
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
                auto res = build_response_step_by_step(board);
                responses.push_back(res);
                mutex.unlock();
            };
            shared_data.hash_length_threshold = request.hash_threshold();
            spdlog::info("Starting solver with board size: {}", board.size);
            spdlog::info("Pieces: {}", pieces.size());
            spdlog::info("Timebetween: {}", request.wait_time());
            spdlog::info("Hash length threshold: {}", request.hash_threshold());

            // launch the solver in a new thread
            std::thread solver_thread(thread_function, board, pieces, std::ref(shared_data));

            // while the solver is running, send the responses to the client
            while (!shared_data.stop)
            {
                co_await delay(std::chrono::milliseconds{request.wait_time()});
                {
                    std::scoped_lock lock(mutex);
                    // only copy the first 10 responses
                    for (int i = 0; i < std::min(10, static_cast<int>(responses.size())); i++)
                    {
                        responses_to_send.push_back(responses[i]);
                    }
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
