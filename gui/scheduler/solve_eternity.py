import humps
import json
import logging
import os
from pathlib import Path

from solve import solve, response_to_dict
from solver.v1 import solver_pb2

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

logger.info('Solving Eternity II')

curr_dir = Path(__file__).parent
output_dir = curr_dir / 'output'
servers = [
    'localhost:50051',
]

if os.environ.get('ETERNITY2_SERVERS'):
    servers = [server.strip() for server in os.environ.get('ETERNITY2_SERVERS').split(',')]

logger.info(f'Using servers: {servers}')
req = json.load(open(curr_dir / 'eternity2.json'))

req = humps.decamelize(req)

logger.info(f'Request: {req}')
request = solver_pb2.SolverSolveRequest(**req)

# Call the server
response = solve(servers, request, store_responses='output/responses.json', sleep_time=req['wait_time'] / 1000 + 1)

# save the response
with open('output/found.json', 'w') as f:
    f.write(json.dumps(response_to_dict(response)))
    f.write('\n')
