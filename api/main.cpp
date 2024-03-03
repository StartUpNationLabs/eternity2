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

template<class Sender>
void run_grpc_context_for_sender(agrpc::GrpcContext &grpc_context, Sender &&sender)
{
    grpc_context.work_started();
    unifex::sync_wait(unifex::when_all(unifex::finally(std::forward<Sender>(sender), unifex::just_from([&] {
                                                           grpc_context.work_finished();
                                                       })),
                                       unifex::just_from([&] { grpc_context.run(); })));
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

    run_grpc_context_for_sender(
        grpc_context,
        unifex::with_query_value(unifex::when_all(handle_server_solver_request_step_by_step(grpc_context,
                                                                                            solver_service),
                                                  handle_server_solver_request(grpc_context, solver_service)),
                                 unifex::get_scheduler,
                                 unifex::inline_scheduler{}));
}
