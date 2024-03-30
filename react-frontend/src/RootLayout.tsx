import ResponsiveAppBar from "./components/ResponsiveAppBar.tsx";
import {Outlet} from "react-router-dom";

export  const  RootLayout = () => {
    return (
        <div>
        <ResponsiveAppBar/>
        <Outlet/>
        </div>
    )
}
