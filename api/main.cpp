// Copyright 2023 Dennis Hezel
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "helper.hpp"
#include "server_shutdown_unifex.hpp"
#include "solver/solvera.h"
#include "solver/v1/solver.grpc.pb.h"

#include <agrpc/asio_grpc.hpp>
#include <agrpc/health_check_service.hpp>
#include <grpcpp/server.h>
#include <grpcpp/server_builder.h>
#include <spdlog/spdlog.h>
#include <unifex/finally.hpp>
#include <unifex/just_from.hpp>
#include <unifex/just_void_or_done.hpp>
#include <unifex/let_value_with.hpp>
#include <unifex/sync_wait.hpp>
#include <unifex/task.hpp>
#include <unifex/then.hpp>
#include <unifex/timed_single_thread_context.hpp>
#include <unifex/when_all.hpp>
#include <unifex/with_query_value.hpp>
// Example showing some of the features of using asio-grpc with libunifex.
unifex::timed_single_thread_context timer;

auto delay(std::chrono::milliseconds ms)
{
    return unifex::schedule_after(timer.get_scheduler(), ms);
}

template<class Sender>
void run_grpc_context_for_sender(agrpc::GrpcContext &grpc_context, Sender &&sender)
{
    grpc_context.work_started();
    unifex::sync_wait(unifex::when_all(unifex::finally(std::forward<Sender>(sender), unifex::just_from([&] {
                                                           grpc_context.work_finished();
                                                       })),
                                       unifex::just_from([&] { grpc_context.run(); })));
}

auto handle_server_solver_request(agrpc::GrpcContext &grpc_context, solver::v1::Solver::AsyncService &service1)
{
    return agrpc::register_sender_rpc_handler<SolverRPC>(
        grpc_context, service1, [&](SolverRPC &rpc, const SolverRPC::Request &request) -> unifex::task<void> {
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

auto main(int argc, const char **argv) -> int
{
    const auto *const port = argc >= 2 ? argv[1] : "50051";
    const auto host        = std::string("0.0.0.0:") + port;
    spdlog::info("Starting server on {}", host);

    solver::v1::Solver::AsyncService solver_service;
    std::unique_ptr<grpc::Server> server;

    grpc::ServerBuilder builder;
    agrpc::GrpcContext grpc_context{builder.AddCompletionQueue()};
    builder.AddListeningPort(host, grpc::InsecureServerCredentials());
    builder.RegisterService(&solver_service);
    agrpc::add_health_check_service(builder);
    server = builder.BuildAndStart();
    abort_if_not(bool{server});
    agrpc::start_health_check_service(*server, grpc_context);

    example::ServerShutdown server_shutdown{*server};

    run_grpc_context_for_sender(grpc_context,
                                unifex::with_query_value(unifex::when_all(
                                                             handle_server_solver_request(grpc_context,
                                                                                          solver_service)),
                                                         unifex::get_scheduler,
                                                         unifex::inline_scheduler{}));
}
