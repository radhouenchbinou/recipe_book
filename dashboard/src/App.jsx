import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth.js";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardLayout from "./pages/DashboardLayout.jsx";
import PortfolioPage from "./pages/PortfolioPage.jsx";
import RecommendationsPage from "./pages/RecommendationsPage.jsx";
import MarketPage from "./pages/MarketPage.jsx";
import AlertsPage from "./pages/AlertsPage.jsx";
import BacktestPage from "./pages/BacktestPage.jsx";
import PerformancePage from "./pages/PerformancePage.jsx";
import RiskPage from "./pages/RiskPage.jsx";
import ReportingPage from "./pages/ReportingPage.jsx";

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/portfolio" replace />} />
        <Route path="portfolio"       element={<PortfolioPage />} />
        <Route path="recommendations" element={<RecommendationsPage />} />
        <Route path="market"          element={<MarketPage />} />
        <Route path="alerts"          element={<AlertsPage />} />
        <Route path="backtest"        element={<BacktestPage />} />
        <Route path="performance"     element={<PerformancePage />} />
        <Route path="risk"            element={<RiskPage />} />
        <Route path="reporting"       element={<ReportingPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
