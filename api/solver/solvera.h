//
// Created by appad on 29/02/2024.
//

#ifndef ETERNITY2_SOLVERA_H
#define ETERNITY2_SOLVERA_H

#include "board/board.h"
#include "solver/solver.h"
#include "solver/v1/solver.grpc.pb.h"

#include <agrpc/asio_grpc.hpp>
#include <spdlog/spdlog.h>
#include <unifex/finally.hpp>
#include <unifex/just_from.hpp>
#include <unifex/let_value_with.hpp>
#include <unifex/sync_wait.hpp>
#include <unifex/task.hpp>
#include <unifex/then.hpp>
#include <unifex/timed_single_thread_context.hpp>
#include <unifex/when_all.hpp>
#include <unifex/with_query_value.hpp>

#include <thread>

auto delay(std::chrono::milliseconds ms) -> unifex::_timed_single_thread_context::_schedule_after_sender<
    std::chrono::duration<long, std::ratio<1, 1000>>>::type;
using SolverService       = solver::v1::Solver::AsyncService;
using SolverRPC           = agrpc::ServerRPC<&SolverService::RequestSolve>;
using SolverStepByStepRPC = agrpc::ServerRPC<&SolverService::RequestSolveStepByStep>;

void thread_function(Board board, std::vector<Piece> pieces, SharedData &shared_data);

auto build_response(const SharedData &shared_data, double elapsed_time) -> SolverRPC::Response;

auto load_board_pieces_from_request(const solver::v1::SolverSolveRequest &request)
    -> std::pair<Board, std::vector<Piece>>;

auto handle_server_solver_request(agrpc::GrpcContext &grpc_context,
                                  solver::v1::Solver::AsyncService &service1) -> unifex::any_sender_of<>;
auto build_response_step_by_step(const Board &board, SharedData &data) -> SolverStepByStepRPC::Response;

auto handle_server_solver_request_step_by_step(agrpc::GrpcContext &grpc_context,
                                               solver::v1::Solver::AsyncService &service1)
    -> unifex::any_sender_of<>;
#endif //ETERNITY2_SOLVERA_H
