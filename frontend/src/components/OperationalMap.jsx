import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "./OperationalMap.css";

const CENTER = [-22.9068, -43.1729];
const CACHE_KEY = "sied-map-geocodes-v1";
const STATUSES = {
  in_progress: ["Em andamento", "#16a34a"], scheduled: ["Programada", "#2563eb"],
  completed: ["Concluída", "#8b98a7"], cancelled: ["Cancelada", "#dc2626"],
  submitted: ["Concluída", "#8b98a7"], pending_report: ["Concluída", "#8b98a7"],
  pending_approval: ["Programada", "#2563eb"],
};
const statusOf = (item) => STATUSES[item.operational_status] || STATUSES.scheduled;
const queryOf = (item) => [item.address, item.neighborhood, item.municipality, "RJ", "Brasil"].filter(Boolean).join(", ");
const readCache = () => { try { return JSON.parse(localStorage.getItem(CACHE_KEY) || "{}"); } catch { return {}; } };
const iconOf = (status) => {
  const [, color] = STATUSES[status] || STATUSES.scheduled;
  return L.divIcon({ className: "sied-marker-wrap", html: `<span class="sied-marker" style="--pin:${color}"><i></i></span>`, iconSize: [34, 42], iconAnchor: [17, 42], popupAnchor: [0, -38] });
};
function Viewport({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0].position, 15);
    else if (points.length > 1) map.fitBounds(points.map((p) => p.position), { padding: [36, 36], maxZoom: 14 });
  }, [map, points]);
  return null;
}

export default function OperationalMap({ operations = [], onOpenAgenda }) {
  const [coordinates, setCoordinates] = useState(readCache);
  const [selected, setSelected] = useState(null);
  const [locating, setLocating] = useState(false);
  const markerRefs = useRef({});
  const mapRef = useRef(null);
  const queries = useMemo(() => operations.map(queryOf), [operations]);

  useEffect(() => {
    let cancelled = false;
    const missing = [...new Set(queries)].filter((query) => query && !(query in coordinates));
    if (!missing.length) return undefined;
    (async () => {
      setLocating(true);
      const next = { ...coordinates };
      for (const query of missing) {
        if (cancelled) break;
        try {
          const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=br&q=${encodeURIComponent(query)}`, { headers: { Accept: "application/json" } });
          const result = await response.json();
          next[query] = result[0] ? [Number(result[0].lat), Number(result[0].lon)] : null;
          setCoordinates({ ...next });
          localStorage.setItem(CACHE_KEY, JSON.stringify(next));
        } catch { next[query] = null; }
        await new Promise((resolve) => window.setTimeout(resolve, 1100));
      }
      if (!cancelled) setLocating(false);
    })();
    return () => { cancelled = true; };
  }, [queries]);

  const points = useMemo(() => operations.map((item) => coordinates[queryOf(item)] ? { ...item, position: coordinates[queryOf(item)] } : null).filter(Boolean), [coordinates, operations]);
  const focus = (item) => {
    const point = points.find((p) => p.id === item.id);
    if (!point || !mapRef.current) return;
    setSelected(item.id);
    mapRef.current.setView(point.position, Math.max(mapRef.current.getZoom(), 15), { animate: true });
    window.setTimeout(() => markerRefs.current[item.id]?.openPopup(), 250);
  };
  const municipalities = new Set(operations.map((i) => i.municipality).filter(Boolean)).size;
  const teams = new Set(operations.map((i) => i.team).filter((i) => i && i !== "Sem equipe")).size;

  return <section className="operational-map-card" aria-labelledby="operational-map-title">
    <header className="operational-map-heading"><div><span>Monitoramento em campo</span><h2 id="operational-map-title">Mapa Operacional de Hoje</h2><p>{operations.length} ações distribuídas em {municipalities} municípios • {teams} equipes em campo</p></div>{locating && <small>Localizando endereços…</small>}</header>
    <div className="operational-map-layout">
      <aside className="operational-map-list" aria-label="Operação em campo"><h3>Operação em Campo</h3>
        {operations.length ? operations.map((item) => { const [label, color] = statusOf(item); const found = Boolean(coordinates[queryOf(item)]); return <button type="button" key={item.id} className={selected === item.id ? "is-active" : ""} onClick={() => focus(item)} disabled={!found} title={found ? `Localizar: ${label}` : "Endereço ainda não localizado"}><i style={{ background: color }} /><strong>{item.time || "--:--"}</strong><span>{item.location || item.title}</span><small>{item.team}</small></button>; }) : <p>Nenhuma ação no período selecionado.</p>}
      </aside>
      <div className="operational-map-canvas">
        <MapContainer center={CENTER} zoom={9} scrollWheelZoom className="operational-leaflet-map" ref={mapRef}><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><Viewport points={points} /><MarkerClusterGroup chunkedLoading showCoverageOnHover={false}>
          {points.map((item) => { const [label, color] = statusOf(item); return <Marker key={item.id} position={item.position} icon={iconOf(item.operational_status)} ref={(marker) => { markerRefs.current[item.id] = marker; }} eventHandlers={{ click: () => setSelected(item.id) }}><Tooltip direction="top" offset={[0, -34]} opacity={1}><strong>{item.type || item.title}</strong><br />{item.time || "--:--"}<br />{item.municipality}<br />Equipe {item.team}<br />Chefe {item.chief}<br />{item.service_order_number ? `OS ${item.service_order_number}` : "Sem OS"}<br />Status: {label}</Tooltip><Popup><div className="operational-map-popup"><strong>{item.type || item.title}</strong><span>{item.time} • {item.location}</span><span>{item.municipality} • Equipe {item.team}</span><span>Chefe {item.chief}</span><b style={{ color }}>{label}</b><button type="button" onClick={() => onOpenAgenda(item.id)}>Abrir agenda</button></div></Popup></Marker>; })}
        </MarkerClusterGroup></MapContainer>
        <div className="operational-map-legend">{[STATUSES.in_progress, STATUSES.scheduled, STATUSES.completed, STATUSES.cancelled].map(([label, color]) => <span key={label}><i style={{ background: color }} />{label}</span>)}</div>
        {!points.length && !locating && operations.length > 0 && <div className="operational-map-no-points">Não foi possível localizar os endereços destas ações.</div>}
      </div>
    </div>
  </section>;
}