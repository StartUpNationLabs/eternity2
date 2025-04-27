import { Box, Card, Grid, Typography } from "@mui/material";
import Board from "../../components/Board.tsx";
import { useRecoilState, useRecoilValue } from "recoil";
import { boardState, hintsState, settingsState } from "../requestForm/atoms.ts";
import { Stats } from "./Stats.tsx";
import { isSolvingState } from "./atoms.ts";
import { useEffect, useState } from "react";
import { abortController, SERVER_BASE_URL } from "../../utils/Constants.tsx";
import { SolverSolveResponse } from "../../proto/solver/v1/solver.ts";
import { GrpcWebFetchTransport } from "@protobuf-ts/grpcweb-transport";
import { SolverClient } from "../../proto/solver/v1/solver.client.ts";

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

            const solverClient = new SolverClient(transport);
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
            };

            console.log("Request object: ", requestOjb);

            const stream = solverClient.solve(requestOjb, {});

            stream.responses.onMessage((message) => {
                setSolverSolveResponse(message);
            });

            stream.responses.onError(() => {
                setSolving(false);
                setStartedSolving(false);
            });

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
        };
    }, []);

    return (
        <Box sx={{ width: '100%', p: 1.5 }}>
            <Grid container spacing={2}>
                {/* Left Column - Stats */}
                <Grid item xs={12} md={3} lg={2}>
                    <Box sx={{ position: 'sticky', top: 24 }}>
                        <Stats response={solverSolveResponse} />
                    </Box>
                </Grid>

                {/* Right Column - Board */}
                <Grid item xs={12} md={9} lg={10}>
                    <Card 
                        elevation={0}
                        sx={{ 
                            p: 2,
                            bgcolor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column'
                        }}
                    >
                        <Typography 
                            variant="subtitle1" 
                            sx={{ 
                                mb: 2,
                                fontWeight: 600,
                                color: 'text.primary'
                            }}
                        >
                            Current Solution
                        </Typography>
                        <Box 
                            sx={{
                                flex: 1,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            <Box
                                sx={{
                                    width: '100%',
                                    maxWidth: '70vh',
                                    aspectRatio: '1/1'
                                }}
                            >
                                <Board 
                                    pieces={solverSolveResponse?.rotatedPieces || []}
                                />
                            </Box>
                        </Box>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
};
