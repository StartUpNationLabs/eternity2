from eternitylib.board import Board
from solve import solve
from solver.v1 import solver_pb2

servers = [
    'localhost:50051',
    'node-apoorva2.k3s.hs.ozeliurs.com:50051',
    'node-apoorva3-abklev50.k3s.hs.ozeliurs.com:50051',
    # 'vmpx15.polytech.hs.ozeliurs.com:50051'
]



if __name__ == '__main__':
    board = Board()
    board.generate(16, 22)

    pieces = [piece.to_grpc() for piece in board.pieces]

    # Create a request
    request = solver_pb2.SolverSolveRequest(
        pieces=pieces,
        threads=50,
        hash_threshold=7,
        wait_time=1000,
        use_cache=True,
        cache_pull_interval=10
    )

    # Call the server
    response = solve(servers, request)

    print(response)
