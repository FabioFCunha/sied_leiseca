import { useState, useEffect, useRef } from "react";
import { useAuth } from "../../context/AuthContext.jsx";
import { Link } from "react-router-dom";
import { api } from "../../api/client.js";
import { formatLocalISODate } from "../../utils/date.js";
import { ChevronRight, Calendar as CalendarIcon, ClipboardList } from "lucide-react";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";

export default function MobileHomePage() {
  const { user } = useAuth();
  
  // Agendas State
  const [agendasCount, setAgendasCount] = useState(null);
  const [loadingAgendas, setLoadingAgendas] = useState(true);
  
  // Escalas State
  const [schedulesCount, setSchedulesCount] = useState(null);
  const [loadingSchedules, setLoadingSchedules] = useState(true);

  const abortAgendasRef = useRef(null);
  const abortSchedulesRef = useRef(null);
  
  const isOperational = ["USER", "SUPERVISOR", "SUPPORT"].includes(user?.role);

  useEffect(() => {
    if (!isOperational) {
      setLoadingAgendas(false);
      setLoadingSchedules(false);
      return;
    }

    const fetchAgendasStats = async () => {
      if (abortAgendasRef.current) abortAgendasRef.current.abort();
      abortAgendasRef.current = new AbortController();
      try {
        const todayStr = formatLocalISODate(new Date());
        const response = await api(`/agendas/?date_from=${todayStr}&date_to=${todayStr}&page_size=1`, { signal: abortAgendasRef.current.signal });
        const count = response.count !== undefined ? response.count : (response.results || response || []).length;
        setAgendasCount(count);
      } catch (err) {
        if (err.name !== "AbortError") setAgendasCount(0);
      } finally {
        setLoadingAgendas(false);
      }
    };

    const fetchSchedulesStats = async () => {
      if (abortSchedulesRef.current) abortSchedulesRef.current.abort();
      abortSchedulesRef.current = new AbortController();
      try {
        const todayStr = formatLocalISODate(new Date());
        const response = await api(`/shift-schedules/?date=${todayStr}&page_size=1`, { signal: abortSchedulesRef.current.signal });
        const count = response.count !== undefined ? response.count : (response.results || response || []).length;
        setSchedulesCount(count);
      } catch (err) {
        if (err.name !== "AbortError") setSchedulesCount(0);
      } finally {
        setLoadingSchedules(false);
      }
    };

    fetchAgendasStats();
    fetchSchedulesStats();

    return () => {
      if (abortAgendasRef.current) abortAgendasRef.current.abort();
      if (abortSchedulesRef.current) abortSchedulesRef.current.abort();
    };
  }, [isOperational]);

  if (!isOperational) {
    return (
      <div className="mobile-alert">
        <p>O modo aplicativo é destinado aos usuários operacionais.</p>
        <p>Utilize a versão completa do SIED para acessar suas funcionalidades.</p>
        <Link to="/" className="mobile-btn mobile-btn-primary" style={{ textDecoration: 'none' }}>
          Abrir versão completa
        </Link>
      </div>
    );
  }

  return (
    <>
      <p style={{ margin: 0, fontSize: "16px" }}>
        Olá, <strong>{user?.full_name?.split(" ")[0] || "Usuário"}</strong>
      </p>
      
      <p style={{ color: "#666", fontSize: "14px", lineHeight: "1.5" }}>
        Bem-vindo ao modo aplicativo do SIED. <br /><br />
        Nesta versão, você terá acesso rápido às funcionalidades operacionais utilizadas em campo.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '8px' }}>
        
        {/* Card Agendas */}
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CalendarIcon size={18} /> Agenda / Ordem de Serviço
          </h3>
          
          {loadingAgendas ? (
            <MobileLoadingState message="Carregando..." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <p style={{ margin: 0, fontSize: '15px', color: '#334155', fontWeight: '500' }}>
                {agendasCount === 0 ? "Nenhuma agenda para hoje." : 
                 agendasCount === 1 ? "1 agenda disponível hoje." : 
                 `${agendasCount} agendas disponíveis hoje.`}
              </p>

              <Link to="/app/agendas" className="mobile-btn mobile-btn-primary" style={{ textDecoration: 'none', justifyContent: 'space-between', padding: '12px 16px' }}>
                Acessar agendas
                <ChevronRight size={20} />
              </Link>
            </div>
          )}
        </div>

        {/* Card Escalas */}
        <div className="mobile-card">
          <h3 className="mobile-card-header" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ClipboardList size={18} /> Minha Escala
          </h3>
          
          {loadingSchedules ? (
            <MobileLoadingState message="Carregando..." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <p style={{ margin: 0, fontSize: '15px', color: '#334155', fontWeight: '500' }}>
                {schedulesCount === 0 ? "Nenhuma escala para hoje." : 
                 schedulesCount === 1 ? "1 equipe escalada hoje." : 
                 `${schedulesCount} equipes escaladas hoje.`}
              </p>

              <Link to="/app/escala" className="mobile-btn mobile-btn-outline" style={{ textDecoration: 'none', justifyContent: 'space-between', padding: '12px 16px', color: '#0a1e44', borderColor: '#0a1e44' }}>
                Visualizar escala
                <ChevronRight size={20} />
              </Link>
            </div>
          )}
        </div>

      </div>
    </>
  );
}
