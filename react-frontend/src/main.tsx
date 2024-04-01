import React from 'react'
import ReactDOM from 'react-dom/client'
import {CssBaseline, Paper, ThemeProvider} from "@mui/material";
import theme from "./theme";
import Test from "./Test.tsx";
import {createBrowserRouter, RouterProvider,} from "react-router-dom";
import {RootLayout} from "./RootLayout";
import {HomePage} from "./pages/homepage/HomePage";
import {RecoilRoot} from "recoil";
import {Solver} from "./pages/solver/Solver.tsx";
import PathManager from "./pages/pathManager/PathManager.tsx";
import {RequestFormStatistics} from "./pages/statistics/RequestFormStatistics.tsx";
import {StatisticsSolver} from "./pages/statistics/StatisticsSolver.tsx";


const router = createBrowserRouter([
    {
        path: "/",
        element: <RootLayout/>,
        children: [
            {
                path: "test",
                element: <Test/>,
            },
            {
                index: true,
                element: <HomePage/>
            },
            {
                path: "path",
                element: <PathManager/>,
            },
            {
                path: "form",
                element: <Paper
                    style={{
                        padding: 20,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "50%",
                        margin: "auto",
                        marginTop: 20,

                    }
                    }
                >
                    <RequestFormStatistics/>
                </Paper>,
            },
            {
                path: "solver",
                element: <Solver/>,
            },
            {
                path: "statistics",
                element: <StatisticsSolver/>,
            }
        ]
    }
])


ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <RecoilRoot>
            <ThemeProvider theme={theme}>
                <CssBaseline/>

                <RouterProvider router={router}/>
            </ThemeProvider>
        </RecoilRoot>
    </React.StrictMode>,
)
