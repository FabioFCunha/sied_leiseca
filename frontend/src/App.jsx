import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AgendaPage from "./pages/AgendaPage.jsx";
import AuditLogsPage from "./pages/AuditLogsPage.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import LookupsPage from "./pages/LookupsPage.jsx";
import GoalsPage from "./pages/GoalsPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import PublicAgendaRequestPage from "./pages/PublicAgendaRequestPage.jsx";
import SetPasswordPage from "./pages/SetPasswordPage.jsx";
import ShiftSchedulePage from "./pages/ShiftSchedulePage.jsx";
import TechnicalReportsPage from "./pages/TechnicalReportsPage.jsx";
import UsersPage from "./pages/UsersPage.jsx";
import StatisticsPage from "./pages/StatisticsPage.jsx";
import SatisfactionSurveyPage from "./pages/SatisfactionSurveyPage.jsx";
import { useAuth } from "./context/AuthContext.jsx";

function HomeRoute() {
  const { user } = useAuth();
  if (user?.role === "VISITOR") {
    return <Navigate to="/calendario" replace />;
  }
  return <DashboardPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/definir-senha" element={<SetPasswordPage />} />
      <Route path="/solicitar-agenda" element={<PublicAgendaRequestPage />} />
      <Route path="/solicitar-agenda/:token" element={<PublicAgendaRequestPage />} />
      <Route path="/pesquisa-satisfacao/:token" element={<SatisfactionSurveyPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomeRoute />} />
        <Route path="agendas" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]}><AgendaPage /></ProtectedRoute>} />
        <Route path="solicitacao-interna" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]}><PublicAgendaRequestPage internalRequest /></ProtectedRoute>} />
        <Route path="calendario" element={<CalendarPage />} />
        <Route path="escala" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"]}><ShiftSchedulePage /></ProtectedRoute>} />
        <Route path="relatorio-tecnico" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]}><TechnicalReportsPage /></ProtectedRoute>} />
        <Route path="relatorios" element={<ProtectedRoute roles={["ADMIN", "MANAGER"]}><ReportsPage /></ProtectedRoute>} />
        <Route path="estatisticas" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]}><StatisticsPage /></ProtectedRoute>} />
        <Route path="metas" element={<ProtectedRoute roles={["ADMIN", "MANAGER"]}><GoalsPage /></ProtectedRoute>} />
        <Route path="cadastros" element={<ProtectedRoute roles={["ADMIN", "MANAGER"]}><LookupsPage /></ProtectedRoute>} />
        <Route path="usuarios" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "CREATOR"]}><UsersPage /></ProtectedRoute>} />
        <Route path="auditoria" element={<ProtectedRoute roles={["CREATOR"]}><AuditLogsPage /></ProtectedRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
