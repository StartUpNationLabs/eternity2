import React from 'react'
import ReactDOM from 'react-dom/client'
import {CssBaseline, ThemeProvider} from "@mui/material";
import theme from "./theme";
import Test from "./Test.tsx";
import {createBrowserRouter, RouterProvider,} from "react-router-dom";
import {RootLayout} from "./RootLayout";
import {HomePage} from "./pages/homepage/HomePage";
import {RequestForm} from "./pages/requestForm/RequestForm.tsx";
import {RecoilRoot} from "recoil";
import PathCreator from "./pages/pathCreator/PathCreator.tsx";


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
                element: <PathCreator/>,
            },
            {
                path: "form",
                element: <RequestForm/>,
            }
        ],
    },
]);

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
