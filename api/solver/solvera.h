//
// Created by appad on 29/02/2024.
//

#ifndef ETERNITY2_SOLVERA_H
#define ETERNITY2_SOLVERA_H

#include <unifex/task.hpp>
#include <agrpc/asio_grpc.hpp>
#include "solver/v1/solver.grpc.pb.h"
#include "board/board.h"
#include "solver/solver.h"

using SolverService = solver::v1::Solver::AsyncService;
using SolverRPC = agrpc::ServerRPC<&SolverService::RequestSolve>;


void thread_function(Board board, std::vector<Piece> pieces, SharedData &shared_data);


SolverRPC::Response build_response(const SharedData &shared_data,
                                   double elapsed_time);

std::pair<Board, std::vector<Piece>> load_board_pieces_from_request(const SolverRPC::Request &request);

#endif //ETERNITY2_SOLVERA_H
