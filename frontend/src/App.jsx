import { lazy, Suspense } from "react";
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
import PublicAgendaRequestPage from "./pages/PublicAgendaRequestPage.jsx";
import SetPasswordPage from "./pages/SetPasswordPage.jsx";
import ShiftSchedulePage from "./pages/ShiftSchedulePage.jsx";
import InspectionReportsPage from "./pages/InspectionReportsPage.jsx";
import TechnicalReportsPage from "./pages/TechnicalReportsPage.jsx";
import UsersPage from "./pages/UsersPage.jsx";
const StatisticsPage = lazy(() => import("./pages/StatisticsPage.jsx"));
const InspectionStatisticsPage = lazy(() => import("./pages/InspectionStatisticsPage.jsx"));
import EvaluationsPage from "./pages/EvaluationsPage.jsx";
import SatisfactionSurveyPage from "./pages/SatisfactionSurveyPage.jsx";
import ReleaseNotesPage from "./pages/ReleaseNotesPage.jsx";
import { useAuth } from "./context/AuthContext.jsx";

// PWA Mobile Components
import MobileLayout from "./components/mobile/MobileLayout.jsx";
import MobileHomePage from "./pages/mobile/MobileHomePage.jsx";
import MobileLoginPage from "./pages/mobile/MobileLoginPage.jsx";
import MobileMorePage from "./pages/mobile/MobileMorePage.jsx";
import MobileAgendasPage from "./pages/mobile/MobileAgendasPage.jsx";
import MobileAgendaDetailsPage from "./pages/mobile/MobileAgendaDetailsPage.jsx";
import MobileReportFormPage from "./pages/mobile/MobileReportFormPage.jsx";
import MobileShiftSchedulesPage from "./pages/mobile/MobileShiftSchedulesPage.jsx";
import MobileShiftScheduleDetailsPage from "./pages/mobile/MobileShiftScheduleDetailsPage.jsx";
import MobileAttendancePage from "./pages/mobile/MobileAttendancePage.jsx";
import MobileShiftAttendancePage from "./pages/mobile/MobileShiftAttendancePage.jsx";
import MobileDesignatedAttendancePage from "./pages/mobile/MobileDesignatedAttendancePage.jsx";
import MobileShiftAttendanceEditPage from "./pages/mobile/MobileShiftAttendanceEditPage.jsx";
import MobileDesignatedAttendanceEditPage from "./pages/mobile/MobileDesignatedAttendanceEditPage.jsx";
import MobileReportsPage from "./pages/mobile/MobileReportsPage.jsx";
import MobileReportDetailsPage from "./pages/mobile/MobileReportDetailsPage.jsx";

function HomeRoute() {
  const { user } = useAuth();
  const inspectionOnly = Array.isArray(user?.access_areas)
    && user.access_areas.includes("INSPECTION")
    && !user.access_areas.includes("EDUCATION");
  return <Navigate to={inspectionOnly ? "/fiscalizacao/estatistica" : "/calendario"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/app/login" element={<MobileLoginPage />} />
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
        <Route path="dashboard" element={<ProtectedRoute moduleName="DASHBOARD"><DashboardPage /></ProtectedRoute>} />
        <Route path="agendas" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]} moduleName="AGENDAS"><AgendaPage /></ProtectedRoute>} />
        <Route path="solicitacao-interna" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]} moduleName="AGENDAS"><PublicAgendaRequestPage internalRequest /></ProtectedRoute>} />
        <Route path="calendario" element={<ProtectedRoute moduleName="CALENDARIO"><CalendarPage /></ProtectedRoute>} />
        <Route path="escala" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "CREATOR"]} moduleName="ESCALA"><ShiftSchedulePage /></ProtectedRoute>} />
        <Route path="relatorio-tecnico" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]} moduleName="RELATORIOS"><TechnicalReportsPage /></ProtectedRoute>} />
        <Route path="fiscalizacao/relatorios" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR", "USER", "SUPPORT", "VISITOR", "ALMOXARIFADO", "CREATOR"]} moduleName="FISCALIZACAO_RELATORIOS"><InspectionReportsPage /></ProtectedRoute>} />
        <Route path="estatisticas" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]} moduleName="ESTATISTICAS"><Suspense fallback={<div className="page">Carregando estatísticas…</div>}><StatisticsPage /></Suspense></ProtectedRoute>} />
        <Route path="fiscalizacao/estatistica" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR", "VISITOR"]} moduleName="FISCALIZACAO_ESTATISTICAS"><Suspense fallback={<div className="page">Carregando estatísticas de Fiscalização...</div>}><InspectionStatisticsPage /></Suspense></ProtectedRoute>} />
        <Route path="avaliacoes" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "SUPERVISOR"]} moduleName="AVALIACOES"><EvaluationsPage /></ProtectedRoute>} />
        <Route path="metas" element={<ProtectedRoute roles={["ADMIN", "MANAGER"]} moduleName="METAS"><GoalsPage /></ProtectedRoute>} />
        <Route path="cadastros" element={<ProtectedRoute roles={["ADMIN", "MANAGER"]} moduleName="CADASTROS"><LookupsPage /></ProtectedRoute>} />
        <Route path="usuarios" element={<ProtectedRoute roles={["ADMIN", "MANAGER", "CREATOR"]} moduleName="USUARIOS"><UsersPage /></ProtectedRoute>} />
        <Route path="auditoria" element={<ProtectedRoute roles={["CREATOR"]} moduleName="AUDITORIA"><AuditLogsPage /></ProtectedRoute>} />
        <Route path="novidades" element={<ReleaseNotesPage />} />
      </Route>

      {/* PWA Mobile Routes */}
      <Route
        path="/app"
        element={
          <ProtectedRoute moduleName="CALENDARIO">
            <MobileLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/app/inicio" replace />} />
        <Route path="inicio" element={<MobileHomePage />} />
        <Route path="agendas" element={<MobileAgendasPage />} />
        <Route path="agendas/:id" element={<MobileAgendaDetailsPage />} />
        <Route path="escala" element={<MobileShiftSchedulesPage />} />
        <Route path="escala/:id" element={<MobileShiftScheduleDetailsPage />} />
        <Route path="frequencia" element={<MobileAttendancePage />} />
        <Route path="frequencia/escala/:id" element={<MobileShiftAttendancePage />} />
        <Route path="frequencia/escala/:id/editar" element={<MobileShiftAttendanceEditPage />} />
        <Route path="frequencia/agenda/:id" element={<MobileDesignatedAttendancePage />} />
        <Route path="frequencia/agenda/:id/editar" element={<MobileDesignatedAttendanceEditPage />} />
        <Route path="relatorios" element={<MobileReportsPage />} />
        <Route path="relatorios/novo/:agendaId" element={<MobileReportFormPage />} />
        <Route path="relatorios/:id/editar" element={<MobileReportFormPage />} />
        <Route path="relatorios/:id" element={<MobileReportDetailsPage />} />
        <Route path="mais" element={<MobileMorePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
