import json
from pathlib import Path

from scheduler.solve import solve, response_to_dict
from scheduler.solver.v1 import solver_pb2
import os

curr_dir = Path(__file__).parent
output_dir = curr_dir / 'output'
servers = [
    'localhost:50051',
]

if os.environ.get('ETERNITY2_SERVERS'):
    servers = [server.strip() for server in os.environ.get('ETERNITY2_SERVERS').split(',')]

req = json.load(open(curr_dir / 'eternity2.json'))

request = solver_pb2.SolverSolveRequest(**req)

# Call the server
response = solve(servers, request, store_responses='output/responses.json', sleep_time=req['wait_time'] / 1000 + 1)

# save the response
with open('output/found.json', 'w') as f:
    f.write(json.dumps(response_to_dict([response])))
    f.write('\n')
