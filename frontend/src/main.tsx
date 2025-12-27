import React, {Suspense} from "react";
import ReactDOM from "react-dom/client";
import {CssBaseline, ThemeProvider} from "@mui/material";
import theme from "./theme.tsx";
import {RecoilRoot} from "recoil";
import {Router} from "@/router.tsx";

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
        <RecoilRoot>
            <ThemeProvider theme={theme}>
                <CssBaseline/>
                <Suspense fallback={<div>Loading...</div>}>
                    <Router />
                </Suspense>
            </ThemeProvider>
        </RecoilRoot>
    </React.StrictMode>
);
