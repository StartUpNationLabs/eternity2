//
// Created by appad on 29/02/2024.
//

#ifndef ETERNITY2_SOLVERA_H
#define ETERNITY2_SOLVERA_H

#include "board/board.h"
#include "solver/solver.h"
#include "solver/v1/solver.grpc.pb.h"

#include <agrpc/asio_grpc.hpp>
#include <unifex/task.hpp>

using SolverService = solver::v1::Solver::AsyncService;
using SolverRPC     = agrpc::ServerRPC<&SolverService::RequestSolve>;

void thread_function(Board board, std::vector<Piece> pieces, SharedData &shared_data);

auto build_response(const SharedData &shared_data, double elapsed_time) -> SolverRPC::Response;

auto load_board_pieces_from_request(const SolverRPC::Request &request)
    -> std::pair<Board, std::vector<Piece>>;

#endif //ETERNITY2_SOLVERA_H
