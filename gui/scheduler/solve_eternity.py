import json
from pathlib import Path

from scheduler.solve import solve, response_to_dict
from scheduler.solver.v1 import solver_pb2

curr_dir = Path(__file__).parent
servers = [
    # 'localhost:50051',
    # 'node-apoorva2.k3s.hs.ozeliurs.com:50051',
    # 'node-apoorva3-abklev50.k3s.hs.ozeliurs.com:50051',
    'vmpx15.polytech.hs.ozeliurs.com:50051',
    # "vmpx15.polytech.hs.ozeliurs.com:50059"
]

req = json.load(open(curr_dir / 'eternity2.json'))

print(req)

request = solver_pb2.SolverSolveRequest(**req)

# Call the server
response = solve(servers, request, store_responses='responses.json', sleep_time=req['wait_time'] / 1000 + 1)

# save the response
with open('found.json', 'w') as f:
    f.write(json.dumps(response_to_dict([response])))
    f.write('\n')
