import {Grid} from "@mui/material";
import Board from "../../components/Board.tsx";
import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, hintsState, settingsState} from "../requestForm/atoms.ts";
import {Stats} from "./Stats.tsx";
import {isSolvingState} from "./atoms.ts";
import {useEffect, useState} from "react";
import {abortController, SERVER_BASE_URL} from "../../utils/Constants.tsx";
import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {SolverClient} from "../../proto/solver/v1/solver.client.ts";


export const Solving = () => {

    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solving, setSolving] = useRecoilState(isSolvingState);
    const [startedSolving, setStartedSolving] = useState(false);
    const [solverSolveResponse, setSolverSolveResponse] = useState<SolverSolveResponse>();
    const [hints,] = useRecoilState(hintsState);

    useEffect(() => {

        if (solving && !startedSolving) {
            setStartedSolving(true);
            console.log("started solving");

            const transport = new GrpcWebFetchTransport({
                baseUrl: SERVER_BASE_URL,
                format: "binary",
                abort: abortController.abortController.signal,
            });

            const solverClient = new SolverClient(
                transport
            );

            console.log("Just before the request: ", hints);

            const requestOjb = {
                hashThreshold: setting.hashThreshold,
                pieces: board,
                threads: setting.threads,
                waitTime: setting.waitTime,
                solvePath: setting.path.path,
                useCache: setting.useCache,
                cachePullInterval: setting.cachePullInterval,
                hints: hints,
            }

            console.log("Request object: ", requestOjb)

            const stream = solverClient.solve(requestOjb, {});

            stream.responses.onMessage((message) => {
                setSolverSolveResponse(message);
            });

            stream.responses.onError(() => {
                    setSolving(false);
                    setStartedSolving(false);
                }
            );

            stream.responses.onComplete(() => {
                setSolving(false);
                setStartedSolving(false);
            });
        }

    }, [solving, startedSolving, board, setting, solverSolveResponse, setSolverSolveResponse, setSolving, hints]);

    useEffect(() => {
        return () => {
            abortController.abortController.abort();
            abortController.abortController = new AbortController();
        }
    }, []);


    return <Grid container spacing={2}
                 style={{
                     minHeight: "90vh",
                     height: '100%',
                     display: 'flex',
                     justifyContent: 'center',
                     alignItems: 'center'
                 }}>
        <Grid item xs={5}>
            <div
                style={{
                    padding: 20,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "100%",
                    margin: "auto",
                    marginTop: 20,
                }}
            >
                <Stats response={solverSolveResponse}/>
            </div>
        </Grid>
        <Grid item xs={4}>
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                aspectRatio: 1,
            }}>
                <div style={{width: "100%", height: "100%"}}>
                    <Board pieces={solverSolveResponse?.rotatedPieces || []}
                    />
                </div>
            </div>
        </Grid>
    </Grid>

}
