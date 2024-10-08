import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import theme from "./theme";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootLayout } from "./RootLayout";
import { RecoilRoot } from "recoil";
import { Solver } from "./pages/solver/Solver.tsx";
import PathManager from "./pages/pathManager/PathManager.tsx";

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
