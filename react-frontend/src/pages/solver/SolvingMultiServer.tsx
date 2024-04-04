import { Grid, Tab, Tabs, Typography} from "@mui/material";

import Board from "../../components/Board.tsx";
import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, settingsState} from "../requestForm/atoms.ts";
import React, {useEffect, useState} from "react";
import {abortController, MULTI_SERVER_BASE_URLS,} from "../../utils/Constants.tsx";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {SolverClient} from "../../proto/solver/v1/solver.client.ts";
import {isSolvingMultiServerState} from "./atoms.ts";
import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";
import {Stats} from "./Stats.tsx";

export const SolvingMultiServer = () => {

    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solvingMultiServer, setsolvingMultiServer] = useRecoilState(isSolvingMultiServerState);
    const [startedsolvingMultiServer, setStartedsolvingMultiServer] = useState(false);
    const [multiServerResponse, setMultiServerResponse] = useState<
        { [key: string]: SolverSolveResponse }
    >();

    const [tabIndex, setTabIndex] = React.useState(0);

    const handleChange = (_: React.SyntheticEvent, newValue: number) => {
        setTabIndex(newValue);
    };
    useEffect(() => {

        if (solvingMultiServer && !startedsolvingMultiServer) {
            setStartedsolvingMultiServer(true);
            console.log("started solvingMultiServer");
            for (const server of MULTI_SERVER_BASE_URLS) {
                const transport = new GrpcWebFetchTransport({
                    baseUrl: server.url,
                    format: "binary",
                    abort: abortController.abortController.signal,

                });

                const solverClient = new SolverClient(
                    transport
                );
                const stream = solverClient.solve({
                    "hashThreshold": setting.hashThreshold,
                    "pieces": board,
                    "threads": setting.threads,
                    "waitTime": setting.waitTime,
                    solvePath: setting.path.path,
                    useCache: setting.useCache,
                    cachePullInterval: setting.cachePullInterval
                }, {});
                stream.responses.onMessage((message) => {
                    setMultiServerResponse((prev) => {
                        return {...prev, [server.url]: message}
                    });
                });

                stream.responses.onError(() => {
                        setsolvingMultiServer(false);
                        setStartedsolvingMultiServer(false);
                    }
                );

                stream.responses.onComplete(() => {
                    setsolvingMultiServer(false);
                    setStartedsolvingMultiServer(false);
                });
            }


        }

    }, [solvingMultiServer, startedsolvingMultiServer, board, setting, setsolvingMultiServer]);

    useEffect(() => {
        return () => {
            abortController.abortController.abort();
            abortController.abortController = new AbortController();
        }
    }, []);


    return (

        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                height: '90vh',
                width: '100%'
            }}
        >
            <Tabs
                value={tabIndex}
                onChange={handleChange}
                textColor="secondary"
                indicatorColor="secondary"
                aria-label="secondary tabs example"
                sx={
                    {
                    }
                }
            >
                {MULTI_SERVER_BASE_URLS.map((key, index) => {
                        return (<Tab label={<Typography

                           variant={"h3"}

                        >{key.name}</Typography>
                            } key={index}/>)
                    }
                )}
            </Tabs>
            <Grid container spacing={2}
                  style={{
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
                    <Stats response={multiServerResponse?.[MULTI_SERVER_BASE_URLS[tabIndex].url]}/>

                </div>
                </Grid>
                <Grid item xs={4}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        height: '100%',
                        aspectRatio: 1,

                    }}
                    >
                        <div style={{width: "100%", height: "100%"}}>
                            <Board pieces={multiServerResponse?.[MULTI_SERVER_BASE_URLS[tabIndex].url]?.rotatedPieces || []}
                            />
                        </div>
                    </div>
                </Grid>
            </Grid>

        </div>
    );


}