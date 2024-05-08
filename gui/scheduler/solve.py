import grpc
import json
import logging
# launch in threads
import threading
import time
from typing import Dict, List

import solver.v1.solver_pb2_grpc as solver_pb2_grpc
from solver.v1 import solver_pb2

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def is_rotated_piece_null(piece: solver_pb2.RotatedPiece):
    return piece.piece.top == 0 and piece.piece.right == 0 and piece.piece.bottom == 0 and piece.piece.left == 0


def equal_rotated_pieces(piece1: solver_pb2.RotatedPiece, piece2: solver_pb2.RotatedPiece):
    return (piece1.piece.top == piece2.piece.top
            and piece1.piece.right == piece2.piece.right
            and piece1.piece.bottom == piece2.piece.bottom
            and piece1.piece.left == piece2.piece.left
            and piece1.rotation == piece2.rotation)


def response_to_dict(server: List[solver_pb2.SolverSolveResponse]):
    out = []
    for response in server:
        out.append({
            "time": response.time,
            "hashes_per_second": response.hashes_per_second,
            "hash_table_size": response.hash_table_size,
            "boards_per_second": response.boards_per_second,
            "boards_analyzed": response.boards_analyzed,
            "hash_table_hits": response.hash_table_hits,
            "rotated_pieces": [
                {
                    "piece": {
                        "top": piece.piece.top,
                        "right": piece.piece.right,
                        "bottom": piece.piece.bottom,
                        "left": piece.piece.left
                    },
                    "rotation": piece.rotation
                } for piece in response.rotated_pieces
            ]
        })
    return out


def solve(_servers: list[str], _request: solver_pb2.SolverSolveRequest, sleep_time: int = 1,
          store_responses: str = None, res_limit: int = 2):
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
            if len(responses[_server]) > res_limit:
                # keep only the last 2 responses to compare them
                responses[_server] = responses[_server][1:]
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
        time.sleep(sleep_time)
        # print
        for server in _servers:
            server_responses = responses[server]
            if store_responses:
                with open(store_responses, 'a') as f:
                    f.write(json.dumps(response_to_dict(server_responses)))
                    f.write('\n')
            if len(server_responses) > 0:
                # count the number of pieces
                piece_count = len(server_responses[-1].rotated_pieces)
                # count the number of null pieces
                null_piece_count = sum(
                    [1 for piece in server_responses[-1].rotated_pieces if is_rotated_piece_null(piece)])
                logger.info(f"Server {server}:")
                logger.info(f"  Time: {server_responses[-1].time}")
                logger.info(f"  Hashes per second: {server_responses[-1].hashes_per_second}")
                logger.info(f"  Hash table size: {server_responses[-1].hash_table_size}")
                logger.info(f"  Boards per second: {server_responses[-1].boards_per_second}")
                logger.info(f"  Boards analyzed: {server_responses[-1].boards_analyzed}")
                logger.info(f"  Hash table hits: {server_responses[-1].hash_table_hits}")
                logger.info(f"  Placed pieces: {piece_count - null_piece_count}/{piece_count}")
                for other_server in _servers:
                    if other_server != server:
                        other_server_responses = responses[other_server]
                        if len(other_server_responses) > 0:
                            # compare the pieces
                            # print the longest common subsequence
                            logger.info(f"  {other_server}:")
                            index = 0
                            while index < min(len(server_responses[-1].rotated_pieces),
                                              len(other_server_responses[-1].rotated_pieces)):
                                if not equal_rotated_pieces(server_responses[-1].rotated_pieces[index],
                                                            other_server_responses[-1].rotated_pieces[index]):
                                    break
                                index += 1
                            logger.info(
                                f"    Longest common subsequence: {index}/{min(len(server_responses[-1].rotated_pieces), len(other_server_responses[-1].rotated_pieces))} with server {other_server}")

    # stop the other threads
    for thread in threads:
        thread.join()
    return found
