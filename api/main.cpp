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

#include "solver/v1/solver.grpc.pb.h"
#include "helper.hpp"
#include "server_shutdown_unifex.hpp"

#include <agrpc/asio_grpc.hpp>
#include <agrpc/health_check_service.hpp>
#include <grpcpp/server.h>
#include <grpcpp/server_builder.h>
#include <unifex/finally.hpp>
#include <unifex/just_from.hpp>
#include <unifex/just_void_or_done.hpp>
#include <unifex/let_value_with.hpp>
#include <unifex/sync_wait.hpp>
#include <unifex/task.hpp>
#include <unifex/then.hpp>
#include <unifex/when_all.hpp>
#include <unifex/with_query_value.hpp>
#include <unifex/timed_single_thread_context.hpp>
// Example showing some of the features of using asio-grpc with libunifex.

using ExampleService = example::v1::Example::AsyncService;

using ServerStreamingRPC = agrpc::ServerRPC<&ExampleService::RequestServerStreaming>;

unifex::timed_single_thread_context timer;
auto delay(std::chrono::milliseconds ms) {
    return unifex::schedule_after(timer.get_scheduler(), ms);
}

auto handle_server_streaming_request(agrpc::GrpcContext &grpc_context, example::v1::Example::AsyncService &service) {
    return agrpc::register_sender_rpc_handler<ServerStreamingRPC>(
            grpc_context, service,
            [&](ServerStreamingRPC &rpc, const ServerStreamingRPC::Request &request) -> unifex::task<void> {
                for (google::protobuf::int32 i = 0; i < request.integer(); ++i) {
                    example::v1::Response response;
                    response.set_integer(i);
                    if (!co_await rpc.write(response)) {
                        // The client hung up.
                        printf("Client hung up\n");
                        co_return;
                    }
                    // sleep for 1 second
                    printf("Sent response %d\n", i);
                    co_await delay(std::chrono::seconds(1));
                }
                co_await rpc.finish(grpc::Status::OK);
            });
}

template<class Sender>
void run_grpc_context_for_sender(agrpc::GrpcContext &grpc_context, Sender &&sender) {
    grpc_context.work_started();
    unifex::sync_wait(
            unifex::when_all(unifex::finally(std::forward<Sender>(sender), unifex::just_from(
                                     [&] {
                                         grpc_context.work_finished();
                                     })),
                             unifex::just_from(
                                     [&] {
                                         grpc_context.run();
                                     })));
}

int main(int argc, const char **argv) {
    const auto port = argc >= 2 ? argv[1] : "50051";
    const auto host = std::string("0.0.0.0:") + port;

    example::v1::Example::AsyncService service;
    std::unique_ptr<grpc::Server> server;

    grpc::ServerBuilder builder;
    agrpc::GrpcContext grpc_context{builder.AddCompletionQueue()};
    builder.AddListeningPort(host, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    agrpc::add_health_check_service(builder);
    server = builder.BuildAndStart();
    abort_if_not(bool{server});
    agrpc::start_health_check_service(*server, grpc_context);

    example::ServerShutdown server_shutdown{*server};

    run_grpc_context_for_sender(
            grpc_context, unifex::with_query_value(unifex::when_all(
                                                           handle_server_streaming_request(grpc_context, service)
                                                   ),
                                                   unifex::get_scheduler, unifex::inline_scheduler{}));
}