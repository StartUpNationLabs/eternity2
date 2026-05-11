import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "./index.css";
import { EducationalRoute } from "./educational/EducationalRoute";
import { ResearchRoute } from "./research/ResearchRoute";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-white">
        <nav className="container mx-auto px-4 py-3 flex gap-6 items-center">
          <Link to="/" className="font-semibold text-lg">Eternity II</Link>
          <Link to="/edu" className="hover:underline">Educational</Link>
          <Link to="/research" className="hover:underline">Research</Link>
        </nav>
      </header>
      <main className="container mx-auto px-4 py-6 flex-1">{children}</main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/edu" replace />} />
          <Route path="/edu/*" element={<Shell><EducationalRoute /></Shell>} />
          <Route path="/research/*" element={<Shell><ResearchRoute /></Shell>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
