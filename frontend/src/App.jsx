import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AgendaPage from "./pages/AgendaPage.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import LookupsPage from "./pages/LookupsPage.jsx";
import GoalsPage from "./pages/GoalsPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import PublicAgendaRequestPage from "./pages/PublicAgendaRequestPage.jsx";
import SetPasswordPage from "./pages/SetPasswordPage.jsx";
import TechnicalReportsPage from "./pages/TechnicalReportsPage.jsx";
import UsersPage from "./pages/UsersPage.jsx";
import StatisticsPage from "./pages/StatisticsPage.jsx";
import SatisfactionSurveyPage from "./pages/SatisfactionSurveyPage.jsx";

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
        <Route index element={<DashboardPage />} />
        <Route path="agendas" element={<AgendaPage />} />
        <Route path="solicitacao-interna" element={<PublicAgendaRequestPage internalRequest />} />
        <Route path="calendario" element={<CalendarPage />} />
        <Route path="relatorio-tecnico" element={<TechnicalReportsPage />} />
        <Route path="relatorios" element={<ReportsPage />} />
        <Route path="estatisticas" element={<StatisticsPage />} />
        <Route path="metas" element={<GoalsPage />} />
        <Route path="cadastros" element={<LookupsPage />} />
        <Route path="usuarios" element={<UsersPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
