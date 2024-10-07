import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, Paper, ThemeProvider } from "@mui/material";
import theme from "./theme";
import Test from "./Test.tsx";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootLayout } from "./RootLayout";
import { HomePage } from "./pages/homepage/HomePage";
import { RecoilRoot } from "recoil";
import { Solver } from "./pages/solver/Solver.tsx";
import PathManager from "./pages/pathManager/PathManager.tsx";
import { RequestFormStatistics } from "./pages/statistics/RequestFormStatistics.tsx";
import { StatisticsSolver } from "./pages/statistics/StatisticsSolver.tsx";

const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <Solver />,
      },
      {
        path: "path",
        element: <PathManager />,
      },
      {
        path: "stats",
        element: <StatisticsSolver />,
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RecoilRoot>
      <ThemeProvider theme={theme}>
        <CssBaseline />

        <RouterProvider router={router} />
      </ThemeProvider>
    </RecoilRoot>
  </React.StrictMode>
);
