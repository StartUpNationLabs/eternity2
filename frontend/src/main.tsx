import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import theme from "./theme.tsx";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootLayout } from "./RootLayout.tsx";
import { RecoilRoot } from "recoil";
import { Solver } from "./pages/solver/Solver.tsx";
import PathManager from "./pages/pathManager/PathManager.tsx";
import DoItYourself from "./pages/doItYourself/DoItYourself.tsx";
import HomePage from "./pages/home/HomePage.tsx";

// Get base path from runtime environment (set by docker-entrypoint.sh)
// This allows deployment under a path prefix (e.g., /eternity2)
let basePath = "/";
try {
  const envResponse = await fetch("/env");
  const envText = await envResponse.text();
  const basepathMatch = envText.match(/BASE_PATH=(.+)/);
  if (basepathMatch && basepathMatch[1]) {
    basePath = basepathMatch[1];
    // Ensure base path starts with / and ends with /
    if (!basePath.startsWith("/")) basePath = "/" + basePath;
    if (!basePath.endsWith("/")) basePath = basePath + "/";
  }
} catch (e) {
  console.log("Using default base path:", basePath);
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "diy",
        element: <DoItYourself />,
      },
      {
        path: "solver",
        element: <Solver />,
      },
      {
        path: "path",
        element: <PathManager />,
      },
    ],
  },
], { basename: basePath });

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
