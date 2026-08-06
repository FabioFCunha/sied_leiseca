import { useState, useEffect, useRef } from "react";
import { formatLocalISODate } from "../../utils/date.js";
import { api } from "../../api/client.js";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, RefreshCw } from "lucide-react";
import MobileAgendaCard from "../../components/mobile/MobileAgendaCard.jsx";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileEmptyState from "../../components/mobile/MobileEmptyState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";

export default function MobileAgendasPage() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [agendas, setAgendas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nextPageUrl, setNextPageUrl] = useState(null);
  const [loadingMore, setLoadingMore] = useState(false);

  // Controle de concorrência com AbortController
  const abortControllerRef = useRef(null);

  const fetchAgendas = async (date, isLoadMore = false) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    if (!isLoadMore) {
      setLoading(true);
      setError(null);
    } else {
      setLoadingMore(true);
    }

    try {
      const dateStr = formatLocalISODate(date);
      // Se não for load more, monta a query para o dia. Se for, usa a url do nextPage (já formatada pelo backend).
      let url = `/agendas/?date_from=${dateStr}&date_to=${dateStr}&page_size=10`;
      
      if (isLoadMore && nextPageUrl) {
        // Garantimos extrair apenas o path+query caso o next venha como URL completa do backend
        try {
          const urlObj = new URL(nextPageUrl);
          url = urlObj.pathname + urlObj.search;
        } catch(e) {
          url = nextPageUrl;
        }
      }

      const response = await api(url, { signal });
      
      if (isLoadMore) {
        setAgendas(prev => [...prev, ...(response.results || [])]);
      } else {
        setAgendas(response.results || response || []);
      }
      
      setNextPageUrl(response.next || null);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Não foi possível carregar as agendas.");
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchAgendas(currentDate);
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [currentDate]);

  const goToPreviousDay = () => {
    const prev = new Date(currentDate);
    prev.setDate(prev.getDate() - 1);
    setCurrentDate(prev);
  };

  const goToNextDay = () => {
    const next = new Date(currentDate);
    next.setDate(next.getDate() + 1);
    setCurrentDate(next);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const handleRefresh = () => {
    fetchAgendas(currentDate);
  };

  const handleLoadMore = () => {
    if (nextPageUrl && !loadingMore) {
      fetchAgendas(currentDate, true);
    }
  };

  // Formatação para exibição: ex: 26/08/2026
  const displayDate = currentDate.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
      
      {/* Date Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'white', padding: '12px 16px', borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
        <button onClick={goToPreviousDay} style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#64748b' }}>
          <ChevronLeft size={24} />
        </button>
        
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#0f172a' }}>{displayDate}</span>
          <button onClick={goToToday} style={{ background: 'none', border: 'none', padding: '4px', fontSize: '12px', color: '#0a1e44', fontWeight: '600', cursor: 'pointer' }}>
            Hoje
          </button>
        </div>

        <button onClick={goToNextDay} style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: '#64748b' }}>
          <ChevronRight size={24} />
        </button>
      </div>

      {/* Header com Atualizar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 4px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', color: '#0a1e44', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CalendarIcon size={20} />
          Agendas
        </h2>
        <button 
          onClick={handleRefresh} 
          disabled={loading}
          aria-label="Atualizar agendas"
          style={{ background: 'none', border: 'none', padding: '8px', color: loading ? '#cbd5e1' : '#0a1e44', cursor: loading ? 'not-allowed' : 'pointer' }}
        >
          <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1 }}>
        {loading ? (
          <MobileLoadingState />
        ) : error ? (
          <MobileErrorState message={error} onRetry={handleRefresh} />
        ) : agendas.length === 0 ? (
          <MobileEmptyState message="Nenhuma agenda encontrada para esta data." />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {agendas.map(agenda => (
              <MobileAgendaCard key={agenda.id} agenda={agenda} />
            ))}
            
            {nextPageUrl && (
              <button 
                onClick={handleLoadMore} 
                disabled={loadingMore}
                className="mobile-btn mobile-btn-outline"
                style={{ marginTop: '8px' }}
              >
                {loadingMore ? "Carregando..." : "Carregar mais"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
