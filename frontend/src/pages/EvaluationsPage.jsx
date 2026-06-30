import { Award, BarChart3, BookOpen, Clock3, Download, HeartHandshake, MessageSquare, Mic, Star, StarHalf, Target, ThumbsUp, TrendingDown, TrendingUp, Users, Zap, Accessibility } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

const emptyFilters = { date_from: "", date_to: "", state: "", municipality: "", status: "", team: "" };

function Stars({ rating }) {
  if (rating === undefined || rating === null) return null;
  const num = Number(rating);
  const full = Math.floor(num);
  const half = num % 1 >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <div style={{ display: "flex", gap: "2px", color: "#f6bd16" }}>
      {Array(full).fill(0).map((_, i) => <Star key={`f-${i}`} size={14} fill="currentColor" />)}
      {half && <StarHalf size={14} fill="currentColor" />}
      {Array(empty).fill(0).map((_, i) => <Star key={`e-${i}`} size={14} opacity={0.3} />)}
    </div>
  );
}

function SatisfactionSummaryPanel({ surveys = {}, onModerateSurvey }) {
  const { overall_rating = 0, total_responses = 0, team_ratings = [], messages = [] } = surveys;
  const { user } = useAuth();
  const isModerator = user?.is_superuser || user?.role === "ADMIN" || user?.role === "MANAGER";
  const overallRating = Number(overall_rating || 0);

  return (
    <div className="chart-card satisfaction-panel" style={{ border: "1px solid var(--line)", borderRadius: "16px", padding: "20px", marginBottom: "24px" }}>
      <div className="section-heading" style={{ marginBottom: "20px" }}>
        <div>
          <h2 style={{ fontSize: "15px", fontWeight: "800" }}>Indicadores de Satisfa&ccedil;&atilde;o</h2>
          <p style={{ fontSize: "12px", color: "var(--text-soft)" }}>Avalia&ccedil;&otilde;es baseadas nas pesquisas de satisfa&ccedil;&atilde;o respondidas.</p>
        </div>
      </div>
      <div className="satisfaction-grid" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div className="overall-rating-card" style={{ background: "var(--surface-2)", padding: "16px", borderRadius: "12px", border: "1px solid var(--line)", display: "flex", alignItems: "center", gap: "16px" }}>
            <div className="overall-rating-value" style={{ fontSize: "40px", fontWeight: "900", color: "var(--text)", lineHeight: 1 }}>{overallRating.toFixed(1)}</div>
            <div>
              <Stars rating={overallRating} />
              <div style={{ fontSize: "12px", color: "var(--text-soft)", marginTop: "4px", fontWeight: "500" }}>Baseado em {total_responses} avalia&ccedil;&otilde;es</div>
            </div>
          </div>

        <div className="satisfaction-messages" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <h3 style={{ fontSize: "13px", fontWeight: "800", color: "var(--text)", margin: 0 }}>Mensagens de feedback</h3>
          
          <style>{`
            @keyframes scrollVertical {
              0% { transform: translateY(0); }
              100% { transform: translateY(-50%); }
            }
          `}</style>
          
          <div className="messages-list-carousel" style={{ maxHeight: "360px", overflow: "hidden", position: "relative" }}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                paddingRight: "4px",
                animation: messages.length > 3 ? "scrollVertical 40s linear infinite" : "none",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.animationPlayState = "paused"; }}
              onMouseLeave={(e) => { e.currentTarget.style.animationPlayState = "running"; }}
            >
              {messages.length ? [...(messages.length > 3 ? [...messages, ...messages] : messages)].map((msg, idx) => (
                <div
                  key={`${msg.id || idx}-${idx}`}
                  className="message-card"
                style={{
                  background: msg.is_approved ? "#fff" : "rgba(246, 189, 22, 0.06)",
                  padding: "12px",
                  borderRadius: "10px",
                  border: msg.is_approved ? "1px solid var(--line)" : "1px solid var(--warning)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  position: "relative",
                  transition: "all 0.2s ease"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <Stars rating={msg.overall_rating} />
                    <span style={{ fontSize: "14px", fontWeight: "800", color: "var(--text)" }}>{Number(msg.overall_rating).toFixed(1)}</span>
                  </div>
                  <span style={{ fontSize: "10px", color: "var(--text-soft)", fontWeight: "700" }}>{msg.answered_at ? new Date(msg.answered_at).toLocaleDateString("pt-BR") : "-"}</span>
                </div>
                <p style={{ margin: 0, fontSize: "15px", color: "var(--text)", lineHeight: 1.5, fontWeight: "500", padding: "4px 0" }}>"{msg.moderated_comment || msg.suggestion}"</p>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    {msg.team && <div style={{ fontSize: "11px", color: "var(--primary)", fontWeight: "800" }}>Equipe: {msg.team}</div>}
                    {msg.agenda__id && <div style={{ fontSize: "10px", color: "var(--text-soft)", fontWeight: "600" }}>OS: #{msg.agenda__id} - {msg.agenda__institution_location || "Local não informado"}</div>}
                  </div>

                  {isModerator && (
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      {msg.moderation_status !== "APPROVED" && (
                        <button
                          onClick={() => onModerateSurvey(msg.id, "APPROVED", msg.moderated_comment || msg.suggestion || "")}
                          style={{
                            background: "var(--primary)",
                            border: "none",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "11px",
                            fontWeight: "800",
                            color: "#fff",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            boxShadow: "0 2px 4px rgba(0,72,215,0.15)"
                          }}
                          type="button"
                        >
                          <ThumbsUp size={11} /> Aprovar
                        </button>
                      )}
                      {msg.moderation_status !== "HIDDEN" && (
                        <button
                          onClick={() => onModerateSurvey(msg.id, "HIDDEN", msg.moderated_comment || msg.suggestion || "")}
                          style={{
                            background: "#fff",
                            border: "1px solid var(--danger)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "11px",
                            fontWeight: "800",
                            color: "var(--danger)",
                            cursor: "pointer"
                          }}
                          type="button"
                        >
                          Ocultar
                        </button>
                      )}
                    </div>
                  )}
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", alignItems: "flex-end" }}>
                    {msg.moderation_status === "APPROVED" && (
                      <span style={{ fontSize: "10px", color: "var(--success)", fontWeight: "700" }}>Aprovado</span>
                    )}
                    {msg.moderation_status === "HIDDEN" && (
                      <span style={{ fontSize: "10px", color: "var(--danger)", fontWeight: "700" }}>Oculto</span>
                    )}
                    {msg.moderation_status === "REJECTED" && (
                      <span style={{ fontSize: "10px", color: "var(--danger)", fontWeight: "700" }}>Recusado</span>
                    )}
                  </div>
                </div>
              </div>
            )) : <p style={{ color: "var(--text-soft)", fontSize: "12px" }}>Nenhum feedback recente.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
const RadarChart = ({ data }) => {
  const svgRef = useRef(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let start = null;
    const animate = (timestamp) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const p = Math.min(elapsed / 800, 1);
      // smoothstep
      setProgress(p * p * (3 - 2 * p));
      if (p < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [data]);

  if (!data || data.length === 0) return null;

  const size = 320;
  const center = size / 2;
  const maxRadius = (size / 2) - 70;
  const angleStep = (Math.PI * 2) / data.length;

  const getPoint = (value, index, radiusScale = 1) => {
    const angle = (Math.PI / 2) - (index * angleStep);
    const r = (value / 5) * maxRadius * radiusScale;
    return {
      x: center + r * Math.cos(angle),
      y: center - r * Math.sin(angle)
    };
  };

  const points = data.map((d, i) => {
    const p = getPoint(d.value * progress, i);
    return `${p.x},${p.y}`;
  }).join(" ");

  return (
    <div className="radar-chart-wrap" style={{ position: "relative", width: "100%", maxWidth: "400px", margin: "0 auto" }}>
      <svg ref={svgRef} viewBox={`0 0 ${size} ${size}`} style={{ width: "100%", height: "auto", overflow: "visible" }}>
        {/* Background Grids */}
        {[1, 2, 3, 4, 5].map((level) => {
          const gridPoints = data.map((_, i) => {
            const p = getPoint(level, i);
            return `${p.x},${p.y}`;
          }).join(" ");
          return (
            <polygon 
              key={level} 
              points={gridPoints} 
              fill={level % 2 === 0 ? "rgba(0,0,0,0.02)" : "none"} 
              stroke="var(--line)" 
              strokeWidth="1" 
              strokeDasharray={level === 5 ? "none" : "2,2"}
            />
          );
        })}

        {/* Axes and Labels */}
        {data.map((d, i) => {
          const p = getPoint(5, i);
          const labelP = getPoint(5, i, 1.15); // Push label out
          let textAnchor = "middle";
          if (Math.abs(Math.cos((Math.PI / 2) - (i * angleStep))) > 0.1) {
            textAnchor = Math.cos((Math.PI / 2) - (i * angleStep)) > 0 ? "start" : "end";
          }
          const words = d.criteria.split(" ");
          let lines = [d.criteria];
          if (words.length > 1 && d.criteria.length > 14) {
            const mid = Math.ceil(words.length / 2);
            lines = [words.slice(0, mid).join(" "), words.slice(mid).join(" ")];
          }

          return (
            <g key={i}>
              <line x1={center} y1={center} x2={p.x} y2={p.y} stroke="var(--line)" strokeWidth="1" />
              <text 
                x={labelP.x} 
                y={labelP.y} 
                textAnchor={textAnchor} 
                dominantBaseline="middle" 
                fontSize="9" 
                fontWeight="600"
                fill="var(--text-soft)"
                style={{ transformOrigin: `${labelP.x}px ${labelP.y}px` }}
              >
                {lines.map((line, idx) => (
                  <tspan key={idx} x={labelP.x} dy={idx === 0 ? (lines.length > 1 ? "-0.5em" : "0") : "1.2em"}>
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          );
        })}

        {/* Data Polygon */}
        <polygon 
          points={points} 
          fill="rgba(0, 72, 215, 0.2)" 
          stroke="var(--primary)" 
          strokeWidth="2" 
          strokeLinejoin="round"
        />

        {/* Data Dots */}
        {data.map((d, i) => {
          const p = getPoint(d.value * progress, i);
          return (
            <circle 
              key={`dot-${i}`} 
              cx={p.x} 
              cy={p.y} 
              r="4" 
              fill="#fff" 
              stroke="var(--primary)" 
              strokeWidth="2"
            >
              <title>{d.criteria}: {d.value}</title>
            </circle>
          );
        })}
      </svg>
    </div>
  );
};

const StackedBarChart = ({ distribution }) => {
  if (!distribution || Object.keys(distribution).length === 0) return null;
  const criteriaList = Object.keys(distribution);
  const colors = {
    "1": "#dc2626",
    "2": "#f97316",
    "3": "#f6bd16",
    "4": "#22c55e",
    "5": "#047857"
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", width: "100%" }}>
      {criteriaList.map((crit, idx) => {
        const counts = distribution[crit];
        const total = Object.values(counts).reduce((a, b) => a + Number(b), 0);
        if (total === 0) return null;

        return (
          <div key={idx} style={{ display: "grid", gridTemplateColumns: "140px 1fr 30px", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-soft)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={crit}>{crit}</span>
            <div style={{ height: "16px", display: "flex", borderRadius: "4px", overflow: "hidden", background: "var(--surface-2)" }}>
              {["1", "2", "3", "4", "5"].map(score => {
                const count = Number(counts[score] || 0);
                if (count === 0) return null;
                const pct = (count / total) * 100;
                return (
                  <div 
                    key={score} 
                    style={{ width: `${pct}%`, height: "100%", background: colors[score], transition: "width 0.5s ease" }}
                    title={`Nota ${score}: ${count} (${pct.toFixed(1)}%)`}
                  />
                );
              })}
            </div>
            <span style={{ fontSize: "11px", fontWeight: "700", textAlign: "right" }}>{total}</span>
          </div>
        );
      })}
      <div className="stacked-bar-legend">
        {["1", "2", "3", "4", "5"].map(score => (
          <span key={score}><i style={{ background: colors[score] }}></i> Nota {score}</span>
        ))}
      </div>
    </div>
  );
};

const EvalLineChart = ({ data }) => {
  const svgRef = useRef(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let start = null;
    const animate = (timestamp) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const p = Math.min(elapsed / 800, 1);
      setProgress(p * p * (3 - 2 * p));
      if (p < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [data]);

  if (!data || data.length === 0) return (
    <div style={{ height: "200px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-soft)" }}>
      Dados insuficientes para evolução mensal
    </div>
  );

  const padding = { top: 30, right: 20, bottom: 30, left: 20 };
  const width = 600;
  const height = 240;
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  // Min and max for y-axis
  const values = data.map(d => d.value);
  const max = 5;
  const min = Math.max(1, Math.floor(Math.min(...values)) - 0.5);

  const getX = (index) => padding.left + (index * (innerWidth / Math.max(1, data.length - 1)));
  const getY = (val) => padding.top + innerHeight - (((val - min) / (max - min)) * innerHeight);

  const points = data.map((d, i) => `${getX(i)},${getY(d.value)}`).join(" ");
  const fillPoints = `${getX(0)},${padding.top + innerHeight} ${points} ${getX(data.length - 1)},${padding.top + innerHeight}`;

  return (
    <div style={{ position: "relative", width: "100%", overflowX: "auto" }}>
      <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", minWidth: "500px" }}>
        <defs>
          <linearGradient id="eval-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Grid Lines */}
        {[min, min + (max-min)/2, max].map((val, i) => (
          <g key={i}>
            <line x1={padding.left} y1={getY(val)} x2={width - padding.right} y2={getY(val)} stroke="var(--line)" strokeDasharray="4 4" />
            <text x={0} y={getY(val)} fontSize="10" fill="var(--text-soft)" dominantBaseline="middle">{val.toFixed(1)}</text>
          </g>
        ))}

        <g style={{ transform: `scaleY(${progress})`, transformOrigin: "bottom" }}>
          {/* Fill */}
          <polygon points={fillPoints} fill="url(#eval-gradient)" />
          {/* Line */}
          <polyline points={points} fill="none" stroke="var(--primary)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        </g>

        {/* Points and Labels */}
        {data.map((d, i) => {
          const cx = getX(i);
          const cy = getY(d.value);
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r="4" fill="#fff" stroke="var(--primary)" strokeWidth="2" style={{ transform: `scale(${progress})`, transformOrigin: `${cx}px ${cy}px` }} />
              <text x={cx} y={padding.top + innerHeight + 16} fontSize="10" fill="var(--text-soft)" textAnchor="middle">{d.label}</text>
              <rect x={cx - 16} y={cy - 24} width="32" height="16" rx="4" fill="var(--text)" style={{ opacity: progress }} />
              <text x={cx} y={cy - 16} fontSize="9" fill="#fff" fontWeight="700" textAnchor="middle" dominantBaseline="middle" style={{ opacity: progress }}>
                {d.value.toFixed(1)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

const EvalHeatmap = ({ heatmap }) => {
  if (!heatmap || heatmap.length === 0) return null;
  const criteriaSet = new Set();
  const monthsSet = new Set();
  heatmap.forEach(h => {
    criteriaSet.add(h.criteria);
    monthsSet.add(h.month);
  });
  const criteriaList = Array.from(criteriaSet);
  const monthsList = Array.from(monthsSet).sort();

  const getValue = (crit, m) => {
    const item = heatmap.find(h => h.criteria === crit && h.month === m);
    return item ? item.value : null;
  };

  const getOpacity = (val) => {
    if (!val) return 0.02;
    return 0.15 + (val / 5) * 0.75; // Map 0-5 to 0.15-0.9
  };

  return (
    <div className="eval-heatmap" style={{ overflowX: "auto", paddingBottom: "8px" }}>
      <div className="eval-heatmap-header" style={{ gridTemplateColumns: `120px repeat(${monthsList.length}, minmax(40px, 1fr))` }}>
        <div />
        {monthsList.map(m => {
          const [yy, mm] = m.split("-");
          return <div key={m}>{mm}/{yy.slice(2)}</div>;
        })}
      </div>
      {criteriaList.map(crit => (
        <div key={crit} className="eval-heatmap-row" style={{ gridTemplateColumns: `120px repeat(${monthsList.length}, minmax(40px, 1fr))` }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={crit}>
            {crit}
          </div>
          {monthsList.map(m => {
            const val = getValue(crit, m);
            return (
              <div 
                key={`${crit}-${m}`} 
                className="eval-heatmap-cell" 
                style={{ 
                  background: val ? `rgba(0, 72, 215, ${getOpacity(val)})` : "var(--surface-2)",
                  color: val > 3 ? "#fff" : "var(--text)"
                }}
                title={`${crit} (${m}): ${val ? val.toFixed(1) : '-'}`}
              >
                {val ? val.toFixed(1) : "-"}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export default function EvaluationsPage() {
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [municipalities, setMunicipalities] = useState([]);
  const [regions, setRegions] = useState([]);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user } = useAuth();
  const canModerate = user?.is_superuser || user?.role === "ADMIN" || user?.role === "MANAGER";

  useEffect(() => {
    Promise.all([
      api("/municipalities/?page_size=500"),
      api("/regions/?page_size=200")
    ]).then(([munRes, regRes]) => {
      setMunicipalities(munRes.results || munRes);
      setRegions(regRes.results || regRes);
    }).catch(console.error);
    api("/teams/?page_size=1000").then((res) => {
      const data = res.results || res;
      const seen = new Set();
      const uniqueTeams = data
        .map(t => ({ ...t, name: String(t.name || "").trim().toUpperCase() }))
        .filter(t => {
          if (!t.name || seen.has(t.name)) return false;
          seen.add(t.name);
          return true;
        })
        .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
      setTeams(uniqueTeams);
    }).catch(console.error);
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString();
      const res = await api(`/surveys/analytics/${params ? `?${params}` : ""}`);
      setData(res);
    } catch (err) {
      setError(err.message || "Erro ao carregar dados de avaliações");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(loadData, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);


  const handleModerationDecision = async (surveyId, status, moderatedComment) => {
    try {
      await api(`/surveys/${surveyId}/moderate/`, {
        method: "POST",
        body: JSON.stringify({ status, moderated_comment: moderatedComment }),
      });
      await loadData();
    } catch (err) {
      console.error(err);
      alert(err.message || "Erro ao moderar comentario.");
    }
  };
  const handleExport = async (format, e) => {
    e.preventDefault();
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString();
      const blob = await api(`/reports/export_${format}/${params ? `?${params}` : ""}`, { responseType: 'blob' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `avaliacoes.${format === "excel" ? "xlsx" : "pdf"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Erro ao exportar. Tente novamente.");
    }
  };

  const availableStates = data?.states || [];
  const availableMunicipalities = data?.municipalities?.length ? data.municipalities : municipalities;

  const cardConfig = [
    { key: "total_surveys", label: "Avaliacoes Recebidas", icon: BarChart3, tone: "blue", format: "int" },
    { key: "satisfaction_index", label: "Indice de Satisfacao", icon: ThumbsUp, tone: "green", format: "percent" },
    { key: "speaker_avg", label: "Nota Palestrante", icon: Mic, tone: "violet", format: "decimal" },
    { key: "resources_avg", label: "Recursos Audiovisuais", icon: BookOpen, tone: "teal", format: "decimal" },
    { key: "punctuality_avg", label: "Pontualidade", icon: Clock3, tone: "blue", format: "decimal" },
    { key: "enthusiasm_avg", label: "Entusiasmo da Equipe", icon: Users, tone: "cyan", format: "decimal" },
    { key: "workshops_avg", label: "Dinamicas", icon: Zap, tone: "amber", format: "decimal" },
    { key: "support_material_avg", label: "Material de Apoio", icon: HeartHandshake, tone: "green", format: "decimal" },
    { key: "wheelchair_avg", label: "Depoimento Cadeirantes", icon: Accessibility, tone: "violet", format: "decimal" },
    { key: "best_criteria", label: "Melhor Criterio", icon: Award, tone: "green", format: "criteria" },
    { key: "worst_criteria", label: "Menor Avaliacao", icon: TrendingDown, tone: "red", format: "criteria" },
    { key: "most_improved", label: "Maior Aumento", icon: TrendingUp, tone: "green", format: "criteria" },
  ];

  return (
    <section className="page evaluations-page" style={{ maxWidth: "1280px", margin: "0 auto", paddingBottom: "40px" }}>
      {/* Hero Banner */}
      <div className="dashboard-hero" style={{ background: "linear-gradient(135deg, #001338 0%, #002d72 100%)", padding: "28px", borderRadius: "16px", color: "#ffffff", marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 8px 32px 0 rgba(0, 19, 56, 0.15)" }}>
        <div>
          <span style={{ fontSize: "11px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "1.5px", color: "#f6bd16", opacity: 0.95, display: "block", marginBottom: "2px" }}>Análise de satisfação</span>
          <h1 style={{ color: "#ffffff", fontSize: "38px", fontWeight: "900", margin: "4px 0", lineHeight: 1 }}>Avaliações</h1>
          <p style={{ margin: 0, color: "#d2e1ff", opacity: 0.9, fontSize: "15px", marginTop: "8px" }}>SISTEMA INTEGRADO DA EDUCAÇÃO - OPERAÇÃO LEI SECA</p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <button onClick={(e) => handleExport("pdf", e)} style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)", color: "#fff", padding: "8px 16px", borderRadius: "8px", display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontWeight: "600", transition: "all 0.2s" }} onMouseOver={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.2)"} onMouseOut={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.1)"}>
            <Download size={16} /> Exportar PDF
          </button>
          <button onClick={(e) => handleExport("excel", e)} style={{ background: "#ffffff", border: "none", color: "#001338", padding: "8px 16px", borderRadius: "8px", display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontWeight: "700", transition: "all 0.2s" }} onMouseOver={(e) => e.currentTarget.style.transform = "translateY(-2px)"} onMouseOut={(e) => e.currentTarget.style.transform = "none"}>
            <Download size={16} /> Excel
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="global-filters" style={{ background: "#ffffff", padding: "16px", borderRadius: "12px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "24px", border: "1px solid var(--line)", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
        <div className="filter-group">
          <label>De</label>
          <input type="date" value={filters.date_from} onChange={(e) => setFilters(f => ({ ...f, date_from: e.target.value }))} />
        </div>
        <div className="filter-group">
          <label>Até</label>
          <input type="date" value={filters.date_to} onChange={(e) => setFilters(f => ({ ...f, date_to: e.target.value }))} />
        </div>
        <div className="filter-group">
          <label>Estado</label>
          <select value={filters.state} onChange={(e) => setFilters(f => ({ ...f, state: e.target.value, municipality: "" }))}>
            <option value="">Todos</option>
            {availableStates.map(state => <option key={state} value={state}>{state}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Região</label>
          <select value={filters.region} onChange={(e) => setFilters(f => ({ ...f, region: e.target.value, municipality: "" }))}>
            <option value="">Todas</option>
            {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Município</label>
          <select value={filters.municipality} onChange={(e) => setFilters(f => ({ ...f, municipality: e.target.value }))}>
            <option value="">Todos</option>
            {availableMunicipalities.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>

        <div className="filter-group">
          <label>Equipe</label>
          <select value={filters.team} onChange={(e) => setFilters(f => ({ ...f, team: e.target.value }))}>
            <option value="">Todas</option>
            {teams.map(team => <option key={team.id} value={team.name}>{team.name}</option>)}
          </select>
        </div>
        <div className="filter-group" style={{ display: "flex", alignItems: "flex-end" }}>
          <button className="secondary" style={{ width: "100%" }} onClick={() => setFilters(emptyFilters)}>Limpar</button>
        </div>
      </div>

      {loading ? (
        <div className="dashboard-skeleton" style={{ padding: "40px", textAlign: "center" }}>
          <div className="spinner" style={{ margin: "0 auto 16px" }} />
          <span style={{ color: "var(--text-soft)" }}>Analisando avaliações...</span>
        </div>
      ) : error ? (
        <div className="alert">{error}</div>
      ) : data ? (
        <>
          <SatisfactionSummaryPanel surveys={data.satisfaction_panel || {}} onModerateSurvey={handleModerationDecision} />
          {/* Metric Cards */}
          <div className="metric-grid" style={{ marginBottom: "24px" }}>
            {cardConfig.map(({ key, label, icon: Icon, tone, format }) => {
              let val = data.cards[key];
              if (format === "decimal" && val != null) val = val.toFixed(2);
              if (format === "percent" && val != null) val = `${val}%`;
              if (val === null || val === undefined) val = "-";
              
              return (
                <button key={key} className={`metric-card ${tone}`} style={{ textAlign: "left", cursor: "default" }}>
                  <div className="metric-icon"><Icon size={20} /></div>
                  <div className="metric-content">
                    <span style={{ fontSize: "12px", color: "var(--text-soft)", fontWeight: "600", display: "block", marginBottom: "4px" }}>{label}</span>
                    <strong style={{ fontSize: format === "criteria" ? "15px" : "22px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={val}>{val}</strong>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="dashboard-layout" style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "24px", alignItems: "start" }}>
            
            {/* Main Column */}
            <div className="dashboard-main" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              
              <div className="analytics-grid">
                <div className="chart-card">
                  <div className="section-heading">
                    <Target size={18} />
                    <h3>Radar de Critérios</h3>
                  </div>
                  <RadarChart data={data.radar} />
                </div>
                <div className="chart-card">
                  <div className="section-heading">
                    <BarChart3 size={18} />
                    <h3>Distribuição das Notas</h3>
                  </div>
                  <StackedBarChart distribution={data.distribution} />
                </div>
              </div>

              <div className="chart-card">
                <div className="section-heading">
                  <TrendingUp size={18} />
                  <h3>Evolução Mensal da Nota Geral</h3>
                </div>
                <EvalLineChart data={data.monthly_evolution} />
              </div>

              <div className="chart-card">
                <div className="section-heading">
                  <BookOpen size={18} />
                  <h3>Mapa de Calor — Critérios por Mês</h3>
                </div>
                <EvalHeatmap heatmap={data.heatmap} />
              </div>

            </div>

            {/* Sidebar Column */}
            <aside className="dashboard-side" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              
              <div className="chart-card">
                <div className="section-heading">
                  <Award size={18} />
                  <h3>Ranking de Equipes</h3>
                </div>
                <div className="ranking-list">
                  {data.ranking.map((item, idx) => {
                    let badge = <span className="rank-position">{idx + 1}º</span>;
                    if (idx === 0) badge = <span className="rank-position" style={{ textShadow: "0 0 8px rgba(255,215,0,0.6)" }}>🥇</span>;
                    if (idx === 1) badge = <span className="rank-position">🥈</span>;
                    if (idx === 2) badge = <span className="rank-position">🥉</span>;

                    return (
                      <div key={item.criteria} className="ranking-item">
                        {badge}
                        <span className="rank-label">{item.criteria}</span>
                        <span className="rank-value">{item.value.toFixed(2)}</span>
                        <div className="rank-bar">
                          <div className="rank-bar-fill" style={{ width: `${(item.value / 5) * 100}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="chart-card">
                <div className="section-heading">
                  <Zap size={18} />
                  <h3>Inteligência</h3>
                </div>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
                  <div className="excellence-ring">
                    <svg viewBox="0 0 36 36" style={{ width: "100%", height: "100%" }}>
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="var(--surface-2)" strokeWidth="3" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="var(--primary)" strokeWidth="3" strokeDasharray={`${data.intelligence.excellence_index}, 100`} />
                    </svg>
                    <strong>{data.intelligence.excellence_index}%</strong>
                  </div>
                </div>
                <div className="intelligence-grid">
                  <div className="intelligence-item">
                    <span className="intelligence-label">Maior Destaque</span>
                    <span className="intelligence-value" style={{ color: "var(--success)" }}>{data.intelligence.best_criteria || "-"}</span>
                  </div>
                  <div className="intelligence-item">
                    <span className="intelligence-label">Maior Crescimento</span>
                    <span className="intelligence-value" style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--success)" }}>
                      {data.intelligence.most_improved ? <><TrendingUp size={14} /> {data.intelligence.most_improved}</> : "-"}
                    </span>
                  </div>
                  <div className="intelligence-item">
                    <span className="intelligence-label">Maior Queda</span>
                    <span className="intelligence-value" style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--danger)" }}>
                      {data.intelligence.most_declined ? <><TrendingDown size={14} /> {data.intelligence.most_declined}</> : "-"}
                    </span>
                  </div>
                  <div className="intelligence-item">
                    <span className="intelligence-label">Tendência (Período)</span>
                    <span className="intelligence-value" style={{ display: "flex", alignItems: "center", gap: "4px", color: data.intelligence.trend === "up" ? "var(--success)" : data.intelligence.trend === "down" ? "var(--danger)" : "var(--text-soft)" }}>
                      {data.intelligence.trend === "up" ? <TrendingUp size={14} /> : data.intelligence.trend === "down" ? <TrendingDown size={14} /> : "-"}
                      {data.intelligence.trend ? `${data.intelligence.trend_delta > 0 ? '+' : ''}${data.intelligence.trend_delta}` : ""}
                    </span>
                  </div>
                </div>
              </div>


            </aside>
          </div>

          {/* Executive Panel */}
          <div className="executive-panel">
            <h2 style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--primary)" }}>
              <Zap size={20} fill="currentColor" />
              Resumo Executivo
            </h2>
            <p>{data.executive_summary}</p>
          </div>

        </>
      ) : null}
    </section>
  );
}
