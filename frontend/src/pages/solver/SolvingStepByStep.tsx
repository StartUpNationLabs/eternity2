import { Box, Card, Grid, Typography } from "@mui/material";
import Board from "../../components/Board.tsx";
import { useRecoilState, useRecoilValue } from "recoil";
import { boardState, hintsState, settingsState } from "../requestForm/atoms.ts";
import { isSolvingStepByStepState } from "./atoms.ts";
import { useEffect, useState } from "react";
import { SolverStepByStepResponse } from "../../proto/solver/v1/solver.ts";
import { SolverClient } from "../../proto/solver/v1/solver.client.ts";
import { abortController, SERVER_BASE_URL } from "../../utils/Constants.tsx";
import { GrpcWebFetchTransport } from "@protobuf-ts/grpcweb-transport";
import { StatsStepByStep } from "./StatsStepByStep.tsx";

export const SolvingStepByStep = () => {
    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solvingStepByStep, setSolvingStepByStep] = useRecoilState(isSolvingStepByStepState);
    const [startedSolvingStepByStep, setStartedSolvingStepByStep] = useState(false);
    const [solverSolveResponse, setSolverSolveResponse] = useState<SolverStepByStepResponse>();
    const [hints,] = useRecoilState(hintsState);

    useEffect(() => {
        if (solvingStepByStep && !startedSolvingStepByStep) {
            setStartedSolvingStepByStep(true);
            console.log("started solvingStepByStep");
            
            const transport = new GrpcWebFetchTransport({
                baseUrl: SERVER_BASE_URL,
                format: "binary",
                abort: abortController.abortController.signal,
            });
            
            const solverClient = new SolverClient(transport);

            const requestObj = {
                hashThreshold: setting.hashThreshold,
                pieces: board,
                threads: setting.threads,
                waitTime: setting.waitTime,
                solvePath: setting.path.path,
                useCache: setting.useCache,
                cachePullInterval: setting.cachePullInterval,
                hints: hints,
                solverVersion: setting.solverVersion,
            };

            console.log("Request object: ", requestObj);

            const stream = solverClient.solveStepByStep(requestObj, {});
            stream.responses.onMessage((message) => {
                setSolverSolveResponse(message);
            });

            stream.responses.onError((error) => {
                console.error(error);
                setSolvingStepByStep(false);
                setStartedSolvingStepByStep(false);
            });

            stream.responses.onComplete(() => {
                console.log("stream ended");
                setSolvingStepByStep(false);
                setStartedSolvingStepByStep(false);
            });
        }
    }, [solvingStepByStep, startedSolvingStepByStep, board, setting, solverSolveResponse, setSolverSolveResponse, setSolvingStepByStep, hints]);

    useEffect(() => {
        return () => {
            abortController.abortController.abort();
            abortController.abortController = new AbortController();
        };
    }, []);

    return (
        <Box sx={{ width: '100%', p: 2 }}>
            <Grid container spacing={3}>
                {/* Stats Section */}
                <Grid item xs={12}>
                    <StatsStepByStep response={solverSolveResponse} />
                </Grid>

                {/* Boards Section */}
                <Grid item xs={12}>
                    <Grid container spacing={3}>
                        {/* Current Board */}
                        <Grid item xs={12} md={6}>
                            <Card 
                                elevation={0}
                                sx={{ 
                                    p: 3,
                                    height: '100%',
                                    bgcolor: 'background.paper',
                                    border: '1px solid',
                                    borderColor: 'divider',
                                }}
                            >
                                <Typography 
                                    variant="h6" 
                                    sx={{ 
                                        mb: 3,
                                        fontWeight: 600,
                                        color: 'text.primary'
                                    }}
                                >
                                    Current Progress
                                </Typography>
                                <Box 
                                    sx={{
                                        width: '100%',
                                        maxWidth: 400,
                                        margin: '0 auto',
                                        aspectRatio: '1/1',
                                    }}
                                >
                                    <Board 
                                        pieces={solverSolveResponse?.rotatedPieces || []}
                                    />
                                </Box>
                            </Card>
                        </Grid>

                        {/* Max Board */}
                        <Grid item xs={12} md={6}>
                            <Card 
                                elevation={0}
                                sx={{ 
                                    p: 3,
                                    height: '100%',
                                    bgcolor: 'background.paper',
                                    border: '1px solid',
                                    borderColor: 'divider',
                                }}
                            >
                                <Typography 
                                    variant="h6" 
                                    sx={{ 
                                        mb: 3,
                                        fontWeight: 600,
                                        color: 'text.primary'
                                    }}
                                >
                                    Best Solution Found
                                </Typography>
                                <Box 
                                    sx={{
                                        width: '100%',
                                        maxWidth: 400,
                                        margin: '0 auto',
                                        aspectRatio: '1/1',
                                    }}
                                >
                                    <Board 
                                        pieces={solverSolveResponse?.maxBoard || []}
                                    />
                                </Box>
                            </Card>
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>
        </Box>
    );
};
