import React, {useState} from 'react'
import {SolverClient} from "./proto/solver/v1/solver.client.ts";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {Piece} from "./components/piece.tsx";

function App() {
    const [count, setCount] = useState(0);
    const transport = new GrpcWebFetchTransport({
        baseUrl: "http://vmpx15.polytech.hs.ozeliurs.com:50052",
        format: "binary",

    });
    const solverClient = new SolverClient(
        transport
    );
    console.log(solverClient);

    const stream = solverClient.solveStepByStep({
        "hashThreshold": 4,
        "pieces": [
            {
                "top": 65535,
                "right": 65535,
                "bottom": 1,
                "left": 1
            },
            {
                "top": 65535,
                "right": 65535,
                "bottom": 1,
                "left": 1
            },
            {
                "top": 65535,
                "right": 65535,
                "bottom": 1,
                "left": 1
            },
            {
                "top": 65535,
                "right": 65535,
                "bottom": 1,
                "left": 1
            }
        ],
        "threads": 4,
        "waitTime": 1,
        useCache: true
    }, {});

    stream.responses.onMessage((message) => {
            console.log(message);
        }
    );


    return (
        <div
            style={{
                textAlign: 'center',
                width: '100vw',
                height: '100vh',
            }}
        >
            <Piece

                piece={{
                    "top": 65535,
                    "right": 65535,
                    "bottom": 1,
                    "left": 1
                }}
            />
        </div>
    )
}

export default App
