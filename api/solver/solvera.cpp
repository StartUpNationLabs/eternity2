//
// Created by appad on 29/02/2024.
//

#include "solvera.h"

#include "board/scan_utils.h"
#include "solvers/v2/solver/solver_v2.h"
#include "solvers/common/utils.h"
#include "solvers/common/constants.h"
#include "solvers/common/logger.h"

#include <unifex/timed_single_thread_context.hpp>
#include <mutex>

// Thread-safe job counter management
namespace {
    unifex::timed_single_thread_context timer;
    
    // Use a mutex-protected structure for job management
    struct JobManager {
        std::mutex mutex;
        std::atomic<int> concurrent_jobs_count{0};
        std::atomic<int> max_concurrent_jobs{-1};
        
        // Initialize max_concurrent_jobs from environment variable
        void initialize() {
            if (max_concurrent_jobs.load() == -1) {
                std::string env_max_jobs = get_env_var("MAX_CONCURRENT_JOBS", "");
                if (!env_max_jobs.empty()) {
                    try {
                        max_concurrent_jobs = eternity2_utils::safe_stoi(env_max_jobs);
                        if (max_concurrent_jobs.load() <= 0) {
                            eternity2_logger::warn("MAX_CONCURRENT_JOBS must be positive, defaulting to {}", 
                                    eternity2_constants::DEFAULT_MAX_CONCURRENT_JOBS);
                            max_concurrent_jobs = eternity2_constants::DEFAULT_MAX_CONCURRENT_JOBS;
                        }
                    } catch (const eternity2_utils::ConversionError& e) {
                        eternity2_logger::error("Invalid MAX_CONCURRENT_JOBS value: {} - {}", env_max_jobs, e.what());
                        max_concurrent_jobs = eternity2_constants::DEFAULT_MAX_CONCURRENT_JOBS;
                    }
                } else {
                    max_concurrent_jobs = eternity2_constants::DEFAULT_MAX_CONCURRENT_JOBS;
                    eternity2_logger::info("MAX_CONCURRENT_JOBS not set in environment. Defaulting to {}.",
                                eternity2_constants::DEFAULT_MAX_CONCURRENT_JOBS);
                }
            }
        }
        
        bool can_start_job() {
            initialize();
            return concurrent_jobs_count.load() < max_concurrent_jobs.load();
        }
        
        void increment_jobs() {
            concurrent_jobs_count++;
        }
        
        void decrement_jobs() {
            concurrent_jobs_count--;
        }
    };
    
    // Global job manager instance
    JobManager job_manager;
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
    eternity2_logger::info("Response built");
    return response;
}

auto build_response_v2(const eternity2_v2::SharedDataV2 &shared_data, double elapsed_seconds) -> SolverRPC::Response
{
    SolverRPC::Response response{};
    const auto &stats = shared_data.stats;
    response.set_boards_analyzed(static_cast<uint32_t>(stats.nodes_explored.load()));
    response.set_hash_table_size(0);  // v2 doesn't use hash table
    response.set_time(elapsed_seconds);
    if (elapsed_seconds > 0) {
        response.set_boards_per_second(static_cast<double>(stats.nodes_explored.load()) / elapsed_seconds);
    } else {
        response.set_boards_per_second(0.0);
    }
    response.set_hashes_per_second(0.0);  // v2 doesn't use hash table
    response.set_hash_table_hits(0);  // v2 doesn't use hash table

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
    eternity2_logger::info("Response built (v2)");
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

auto build_response_step_by_step_v2(const Board &board, const eternity2_v2::SharedDataV2 &data, double elapsed_seconds) -> SolverStepByStepRPC::Response
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
    const auto &stats = data.stats;
    response.set_boards_analyzed(static_cast<uint32_t>(stats.nodes_explored.load()));
    response.set_time(elapsed_seconds);
    if (elapsed_seconds > 0) {
        response.set_boards_per_second(static_cast<double>(stats.nodes_explored.load()) / elapsed_seconds);
    } else {
        response.set_boards_per_second(0.0);
    }
    response.set_steps(static_cast<uint32_t>(stats.pieces_placed.load()));
    return response;
}

auto load_board_pieces_from_request(const solver::v1::SolverSolveRequest &request)
    -> std::pair<Board, std::vector<Piece>>
{
    const auto &req_pieces = request.pieces();
    const auto size        = req_pieces.size();
    eternity2_logger::info("Loading board and pieces from request");
    eternity2_logger::info("Loaded {} pieces", size);
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
        eternity2_logger::info("Using custom solve path");
        board.next_index_cache = {request.solve_path().begin(), request.solve_path().end()};
        // log the solve path
        std::string solve_path = "Solve path: ";
        for (const auto &index : board.next_index_cache)
        {
            solve_path += std::to_string(index) + " ";
        }
        eternity2_logger::info(solve_path);
    }
    else
    {
        eternity2_logger::info("Using default solve path");
    }
    // add the hints pieces
    for (const auto &hint : request.hints())
    {
        eternity2_logger::info("Placing hint piece");
        eternity2_logger::info("Hint: x: {}, y: {}, rotation: {}", hint.x(), hint.y(), hint.rotation());
        auto index    = std::make_pair(hint.x(), hint.y());
        auto index_1d = get_1d_board_index(board, index);
        eternity2_logger::info("Index 1d: {}", index_1d);
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

void thread_function_v2(Board board, std::vector<Piece> pieces, eternity2_v2::SharedDataV2 &shared_data)
{
    eternity2_v2::solve_board_v2(board, pieces, shared_data);
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
    eternity2_logger::info("Hash: {}", hash);
    return hash;
}

auto handle_server_solver_request(agrpc::GrpcContext &grpc_context,
                                  solver::v1::Solver::AsyncService &service1) -> unifex::any_sender_of<>
{
    return agrpc::register_sender_rpc_handler<SolverRPC>(
        grpc_context, service1, [&](SolverRPC &rpc, SolverRPC::Request &request) -> unifex::task<void> {
            eternity2_logger::info("Received request");
                const auto &req_pieces = request.pieces();
                const auto size        = req_pieces.size();
                if (size == 0){
                    co_return;
                }
            if (!job_manager.can_start_job())
            {
                eternity2_logger::info("Too many concurrent jobs ({} / {})", 
                            job_manager.concurrent_jobs_count.load(), 
                            job_manager.max_concurrent_jobs.load());
                co_return;
            }
            job_manager.increment_jobs();
            auto [board, pieces] = load_board_pieces_from_request(request);
            
            // Check solver version (defaults to V1 if not set)
            auto solver_version = request.solver_version();
            bool use_v2 = (solver_version == solver::v1::SolverVersion::V2);
            
            if (use_v2) {
                eternity2_logger::info("Using solver v2");
                // V2 implementation
                std::mutex mutex;
                Board max_board = create_board(board.size);
                eternity2_v2::SharedDataV2 shared_data = {max_board, {0}, mutex};
                shared_data.config.collect_stats = true;
                shared_data.config.verbose = false;
                
                auto start = std::chrono::high_resolution_clock::now();
                eternity2_logger::info("Starting solver v2 with board size: {}", board.size);
                eternity2_logger::info("Pieces: {}", pieces.size());
                eternity2_logger::info("Timebetween: {}", request.wait_time());
                
                // V2 runs single-threaded per instance, but we can run multiple instances
                int max_thread_count = std::max(4, static_cast<int>(std::thread::hardware_concurrency()));
                int thread_count = std::min(max_thread_count, static_cast<int>(request.threads()));
                std::vector<std::thread> threads;
                threads.reserve(thread_count);
                
                // Create multiple solver instances (each runs in its own thread)
                for (int i = 0; i < thread_count; i++)
                {
                    threads.emplace_back(thread_function_v2, board, pieces, std::ref(shared_data));
                }
                
                auto last_cache_pull = std::chrono::high_resolution_clock::now();
                if (request.use_cache())
                {
                    eternity2_logger::info("Using cache (v2 doesn't support cache yet)");
                    last_cache_pull = std::chrono::high_resolution_clock::now();
                }
                eternity2_logger::info("Solver v2 started");
                
                while (true)
                {
                    co_await delay(std::chrono::milliseconds{request.wait_time()});
                    double seconds_since_start = static_cast<double>(
                                                     std::chrono::duration_cast<std::chrono::milliseconds>(
                                                         std::chrono::high_resolution_clock::now() - start)
                                                         .count())
                                                 / 1000.0;

                    if (shared_data.max_count.load() == static_cast<long long>(board.size * board.size))
                    {
                        eternity2_logger::info("Found solution (v2)");
                        job_manager.decrement_jobs();
                        shared_data.stop = true;
                        for (auto &thread : threads)
                        {
                            thread.join();
                        }
                        eternity2_logger::info("Threads stopped (v2)");
                        co_await rpc.write(build_response_v2(shared_data, seconds_since_start));
                        co_await rpc.finish(grpc::Status::OK);
                        co_return;
                    }
                    eternity2_logger::info("Writing response (v2)");
                    if (!co_await rpc.write(build_response_v2(shared_data, seconds_since_start)))
                    {
                        eternity2_logger::info("Client cancelled request (v2)");
                        job_manager.decrement_jobs();
                        shared_data.stop = true;
                        for (auto &thread : threads)
                        {
                            thread.join();
                        }
                        eternity2_logger::info("Threads stopped (v2)");
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
                    eternity2_logger::info("Response written (v2)");
                }
            } else {
                eternity2_logger::info("Using solver v1");
                // V1 implementation (existing code)
                std::mutex mutex;
                Board max_board = create_board(board.size);
                int max_count   = 0;
                std::vector<std::thread> threads;
                int max_thread_count = std::max(4, static_cast<int>(std::thread::hardware_concurrency()));
                int thread_count     = std::min(max_thread_count, static_cast<int>(request.threads()));

                eternity2_logger::info("Starting solver with board size: {}", board.size);
                eternity2_logger::info("Using {} threads", thread_count);
                eternity2_logger::info("Pieces: {}", pieces.size());
                eternity2_logger::info("Timebetween: {}", request.wait_time());
                eternity2_logger::info("Hash length threshold: {}", request.hash_threshold());

                threads.reserve(thread_count);
                std::unordered_set<BoardHash> hashes = {};
                SharedData shared_data               = {max_board, max_count, mutex, hashes};
                shared_data.hash_length_threshold    = request.hash_threshold();
                auto start                           = std::chrono::high_resolution_clock::now();
                auto pieces_hash                     = hash_pieces_board(pieces, board);

                auto last_cache_pull = std::chrono::high_resolution_clock::now();
                if (request.use_cache())
                {
                    eternity2_logger::info("Using cache");
                    last_cache_pull = std::chrono::high_resolution_clock::now();
                }
                eternity2_logger::info("Starting solver", board.size);

                for (int i = 0; i < thread_count; i++)
                {
                    threads.emplace_back(thread_function, board, pieces, std::ref(shared_data));
                }
            eternity2_logger::info("Solver started");
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
                    eternity2_logger::info("Found solution");
                    // stop threads
                    eternity2_logger::info("Stopping threads");
                    job_manager.decrement_jobs();
                    shared_data.stop = true;
                    for (auto &thread : threads)
                    {
                        // force stop
                        thread.join();
                    }
                    eternity2_logger::info("Threads stopped");
                    co_await rpc.write(build_response(shared_data, seconds_since_start));
                    auto step_by_step = build_response_step_by_step(shared_data.max_board, shared_data);
                    std::string out   = std::string();
                    step_by_step.AppendToString(&out);

                    co_await rpc.finish(grpc::Status::OK);
                    co_return;
                }
                eternity2_logger::info("Writing response");
                if (!co_await rpc.write(build_response(shared_data, seconds_since_start)))
                {
                    eternity2_logger::info("Client cancelled request");
                    job_manager.decrement_jobs();
                    eternity2_logger::info("Stopping threads");
                    // stop threads
                    shared_data.stop = true;
                    for (auto &thread : threads)
                    {
                        // force stop
                        thread.join();
                    }
                    eternity2_logger::info("Threads stopped");
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
                eternity2_logger::info("Response written");
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
            eternity2_logger::info("Received StepByStep request");
            auto [board, pieces] = load_board_pieces_from_request(request);
            
            // Check solver version (defaults to V1 if not set)
            auto solver_version = request.solver_version();
            bool use_v2 = (solver_version == solver::v1::SolverVersion::V2);
            
            if (use_v2) {
                eternity2_logger::info("Using solver v2 (step by step)");
                std::mutex mutex;
                Board max_board = create_board(board.size);
                eternity2_v2::SharedDataV2 shared_data = {max_board, {0}, mutex};
                shared_data.config.collect_stats = true;
                shared_data.config.verbose = false;
                
                auto start = std::chrono::high_resolution_clock::now();
                std::vector<SolverStepByStepRPC::Response> responses;
                std::vector<SolverStepByStepRPC::Response> responses_to_send;
                shared_data.on_board_update = [&](const Board &board) {
                    std::scoped_lock lock(mutex);
                    auto elapsed_seconds = static_cast<double>(
                        std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::high_resolution_clock::now() - start).count()) / 1000.0;
                    auto res = build_response_step_by_step_v2(board, shared_data, elapsed_seconds);
                    responses.push_back(res);
                };
                
                eternity2_logger::info("Starting solver v2 with board size: {}", board.size);
                eternity2_logger::info("Pieces: {}", pieces.size());
                eternity2_logger::info("Timebetween: {}", request.wait_time());
                
                // launch the solver in a new thread
                std::thread solver_thread(thread_function_v2, board, pieces, std::ref(shared_data));

                // while the solver is running, send the responses to the client
                while (!shared_data.stop.load())
                {
                    co_await delay(std::chrono::milliseconds{request.wait_time()});
                    {
                        std::scoped_lock lock(mutex);
                        // only copy the last N responses
                        responses_to_send = {responses.end() - std::min(static_cast<int>(responses.size()), 
                                         static_cast<int>(eternity2_constants::MAX_RESPONSES_TO_SEND)),
                                         responses.end()};
                        responses.clear();
                    }
                    for (auto const &res : responses_to_send)
                    {
                        if (!co_await rpc.write(res))
                        {
                            eternity2_logger::info("Client cancelled request (v2)");
                            shared_data.stop = true;
                            eternity2_logger::info("Stopping solver thread (v2)");
                            solver_thread.join();
                            eternity2_logger::info("Solver thread stopped (v2)");
                            co_await rpc.finish(grpc::Status::CANCELLED);
                            co_return;
                        }
                    }
                    responses_to_send.clear();
                }
                solver_thread.join();
                co_await rpc.finish(grpc::Status::OK);
                co_return;
            } else {
                eternity2_logger::info("Using solver v1 (step by step)");
                // V1 implementation (existing code)
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
                eternity2_logger::info("Starting solver with board size: {}", board.size);
                eternity2_logger::info("Pieces: {}", pieces.size());
                eternity2_logger::info("Timebetween: {}", request.wait_time());
                eternity2_logger::info("Hash length threshold: {}", request.hash_threshold());
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
                        // only copy the last N responses
                        responses_to_send = {responses.end() - std::min(static_cast<int>(responses.size()), 
                                         static_cast<int>(eternity2_constants::MAX_RESPONSES_TO_SEND)),
                                         responses.end()};
                        responses.clear();
                    }
                    for (auto const &res : responses_to_send)
                    {
                        if (!co_await rpc.write(res))
                        {
                            eternity2_logger::info("Client cancelled request");
                            shared_data.stop = true;
                            eternity2_logger::info("Stopping solver thread");
                            solver_thread.join();
                            eternity2_logger::info("Solver thread stopped");
                            co_await rpc.finish(grpc::Status::CANCELLED);
                            co_return;
                        }
                    }
                    responses_to_send.clear();
                }
                solver_thread.join();
                co_await rpc.finish(grpc::Status::OK);
                co_return;
            }
        });
}
