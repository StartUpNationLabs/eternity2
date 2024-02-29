#include <cstdio>
#include <optional>

#include <grpcxx/server.h>
#include "helloworld/v1/greeter.grpcxx.pb.h"



// Implement rpc application logic using template specialisation for generated `ServiceImpl` struct
template <>
helloworld::v1::Greeter::rpcHello::result_type helloworld::v1::Greeter::ServiceImpl::call<helloworld::v1::Greeter::rpcHello>(
        grpcxx::context &, const GreeterHelloRequest &req) {
    GreeterHelloResponse res;
    res.set_message("Hello `" + req.name() + req.language() + "` 👋");
    return {grpcxx::status::code_t::ok, res};
}

helloworld::v1::Solver::rpcSolve::result_type helloworld::v1::Solver::ServiceImpl::call(grpcxx::context &,
                                                                                        const typename T::request_type &) {
    return {grpcxx::status::code_t::ok, typename T::response_type{}};
}


int main() {
    helloworld::v1::Greeter::ServiceImpl greeter;
    helloworld::v1::Greeter::Service     service(greeter);

    grpcxx::server server;
    server.add(service);

    std::printf("Listening on [127.0.0.1:7000] ...\n");
    server.run("127.0.0.1", 7000);

    return 0;
}