import { lazy, Suspense, type ReactNode } from "react";
import { RouterProvider, createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import RequirePmRole from "./auth/RequirePmRole";
import RequireRole from "./auth/RequireRole";
import { RoleProvider } from "./auth/RoleContext";
import Layout from "./layout/Layout";
import Login from "./pages/Login";

const Home = lazy(() => import("./pages/Home"));
const About = lazy(() => import("./pages/About"));
const Services = lazy(() => import("./pages/Services"));
const Team = lazy(() => import("./pages/Team"));
const Contact = lazy(() => import("./pages/Contact"));
const Projects = lazy(() => import("./pages/Projects"));
const ResearchResults = lazy(() => import("./pages/ResearchResults"));
const ResearchSession = lazy(() => import("./pages/ResearchSession"));
const Downloads = lazy(() => import("./pages/Downloads"));
const ClientAccess = lazy(() => import("./pages/ClientAccess"));
const ClientProject = lazy(() => import("./pages/ClientProject"));

function ProductRoute({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="route-loading" role="status">Loading workspace…</div>}>{children}</Suspense>;
}

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/client", element: <Navigate to="/client/access" replace /> },
  { path: "/client/access", element: <ProductRoute><ClientAccess /></ProductRoute> },
  { path: "/client/project/:projectId", element: <ProductRoute><ClientProject /></ProductRoute> },
  {
    element: <Layout />,
    children: [
      { path: "/", element: <ProductRoute><Home /></ProductRoute> },
      { path: "/about", element: <ProductRoute><About /></ProductRoute> },
      { path: "/team", element: <ProductRoute><Team /></ProductRoute> },
      { path: "/contact", element: <ProductRoute><Contact /></ProductRoute> },
      {
        element: <RequireRole><Outlet /></RequireRole>,
        children: [
          {
            element: <RequirePmRole><Outlet /></RequirePmRole>,
            children: [
              { path: "/projects", element: <ProductRoute><Projects /></ProductRoute> },
              { path: "/projects/:projectId/results", element: <ProductRoute><ResearchResults /></ProductRoute> },
              { path: "/projects/:projectId/sessions/:sessionId", element: <ProductRoute><ResearchSession /></ProductRoute> },
              { path: "/downloads", element: <ProductRoute><Downloads /></ProductRoute> },
            ],
          },
          {
            path: "/services",
            element: (
              <RequirePmRole>
                <ProductRoute><Services /></ProductRoute>
              </RequirePmRole>
            ),
          },
        ],
      },
    ],
  },
]);

export default function App() {
  return (
    <RoleProvider>
      <RouterProvider router={router} />
    </RoleProvider>
  );
}
