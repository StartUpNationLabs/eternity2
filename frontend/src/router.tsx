import {useEffect, useState} from "react";
import {createBrowserRouter, RouterProvider} from "react-router-dom";
import {loadEnv, PREFIX} from "@/utils/Constants.tsx";
import {RootLayout} from "@/RootLayout.tsx";
import HomePage from "@/pages/home/HomePage.tsx";
import DoItYourself from "@/pages/doItYourself/DoItYourself.tsx";
import {Solver} from "@/pages/solver/Solver.tsx";
import PathManager from "@/pages/pathManager/PathManager.tsx";

export const Router = () => {
    const [envLoaded, setEnvLoaded] = useState(false);

    useEffect(() => {
        const fetchEnv = async () => {
            await loadEnv();
            setEnvLoaded(true);
        };
        fetchEnv();
    }, []);

    if (!envLoaded) {
        return <div>Loading environment...</div>;
    }

    const router = createBrowserRouter([
        {
            path: "/",
            element: <RootLayout/>,
            children: [
                {
                    index: true,
                    element: <HomePage/>,
                },
                {
                    path: "diy",
                    element: <DoItYourself/>,
                },
                {
                    path: "solver",
                    element: <Solver/>,
                },
                {
                    path: "path",
                    element: <PathManager/>,
                },
            ],
        },
    ], {
        basename: PREFIX,
    });

    return <RouterProvider router={router}/>;
};
