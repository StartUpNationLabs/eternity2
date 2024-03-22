from typing import Dict

import grpc
import solver.v1.solver_pb2_grpc as solver_pb2_grpc
import time
# launch in threads
import threading

from solver.v1 import solver_pb2
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def solve(_servers: list[str], _request: solver_pb2.SolverSolveRequest):
    stubs = map(lambda _server: (_server, solver_pb2_grpc.SolverStub(grpc.insecure_channel(_server))), _servers)

    # Make the
    responses: Dict[str, list[
        solver_pb2.SolverSolveResponse
    ]] = {}
    for server in _servers:
        responses[server] = []

    found = [False]

    def internal_solve(server_stub: tuple[str, solver_pb2_grpc.SolverStub], _request: solver_pb2.SolverSolveRequest,
                       _found: list[bool | solver_pb2.SolverSolveResponse]):
        _stub = server_stub[1]
        _server = server_stub[0]
        for _response in _stub.Solve(_request):
            responses[_server].append(_response)
            if _found[0]:
                return
        _found[0] = responses[_server][-1]

    threads = []
    for stub in stubs:
        thread = threading.Thread(target=internal_solve, args=(stub, _request, found))
        threads.append(thread)
        thread.start()

    # if a thread has finished before the others, stop the others
    while not found[0]:
        time.sleep(1)
        # print
        for server in _servers:
            server_responses = responses[server]
            if len(server_responses) > 0:
                # count the number of pieces
                piece_count = len(server_responses[-1].rotated_pieces)
                # count the number of null pieces
                null_piece_count = sum([1 for piece in server_responses[-1].rotated_pieces if piece.piece.top == 0 and piece.piece.right == 0 and piece.piece.bottom == 0 and piece.piece.left == 0])
                logger.info(f"Server {server}:")
                logger.info(f"  Time: {server_responses[-1].time}")
                logger.info(f"  Hashes per second: {server_responses[-1].hashes_per_second}")
                logger.info(f"  Hash table size: {server_responses[-1].hash_table_size}")
                logger.info(f"  Boards per second: {server_responses[-1].boards_per_second}")
                logger.info(f"  Boards analyzed: {server_responses[-1].boards_analyzed}")
                logger.info(f"  Hash table hits: {server_responses[-1].hash_table_hits}")
                logger.info(f"  Placed pieces: {piece_count - null_piece_count}/{piece_count}")

    # stop the other threads
    for thread in threads:
        thread.join()
    return found
