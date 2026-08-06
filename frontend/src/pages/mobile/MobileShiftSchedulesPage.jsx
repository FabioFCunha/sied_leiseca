import { useState, useEffect, useRef } from "react";
import { formatLocalISODate } from "../../utils/date.js";
import { api } from "../../api/client.js";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, RefreshCw, ClipboardList } from "lucide-react";
import MobileShiftScheduleCard from "../../components/mobile/MobileShiftScheduleCard.jsx";
import MobileLoadingState from "../../components/mobile/MobileLoadingState.jsx";
import MobileEmptyState from "../../components/mobile/MobileEmptyState.jsx";
import MobileErrorState from "../../components/mobile/MobileErrorState.jsx";

export default function MobileShiftSchedulesPage() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nextPageUrl, setNextPageUrl] = useState(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const abortControllerRef = useRef(null);

  const fetchSchedules = async (date, isLoadMore = false) => {
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
      let url = `/shift-schedules/?date=${dateStr}&page_size=20`;
      
      if (isLoadMore && nextPageUrl) {
        try {
          const urlObj = new URL(nextPageUrl);
          url = urlObj.pathname + urlObj.search;
        } catch(e) {
          url = nextPageUrl;
        }
      }

      const response = await api(url, { signal });
      
      if (isLoadMore) {
        setSchedules(prev => [...prev, ...(response.results || [])]);
      } else {
        setSchedules(response.results || response || []);
      }
      
      setNextPageUrl(response.next || null);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Não foi possível carregar as escalas.");
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchSchedules(currentDate);
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
    fetchSchedules(currentDate);
  };

  const handleLoadMore = () => {
    if (nextPageUrl && !loadingMore) {
      fetchSchedules(currentDate, true);
    }
  };

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
          <ClipboardList size={20} />
          Minha Escala
        </h2>
        <button 
          onClick={handleRefresh} 
          disabled={loading}
          aria-label="Atualizar escala"
          style={{ background: 'none', border: 'none', padding: '8px', color: loading ? '#cbd5e1' : '#0a1e44', cursor: loading ? 'not-allowed' : 'pointer' }}
        >
          <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1 }}>
        {loading ? (
          <MobileLoadingState message="Carregando escalas..." />
        ) : error ? (
          <MobileErrorState message={error} onRetry={handleRefresh} />
        ) : schedules.length === 0 ? (
          <MobileEmptyState message="Nenhuma escala encontrada para esta data." />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {schedules.map(schedule => (
              <MobileShiftScheduleCard key={schedule.id} schedule={schedule} />
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
