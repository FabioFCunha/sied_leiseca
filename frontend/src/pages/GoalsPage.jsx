import { Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { defaultGoalRows, flattenGoalRows } from "../utils/educationGoals.js";

const currentYear = new Date().getFullYear();

function numberValue(value) {
  return Number(value || 0);
}

export default function GoalsPage() {
  const [year, setYear] = useState(currentYear);
  const [savedGoals, setSavedGoals] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const baseRows = useMemo(() => flattenGoalRows(defaultGoalRows), []);
  const rows = useMemo(
    () => baseRows.map((row, index) => {
      const savedGoal = savedGoals.find((goal) => goal.key === row.key);
      const draft = drafts[row.key] || {};
      return {
        ...row,
        id: savedGoal?.id,
        order: index + 1,
        average: draft.average ?? savedGoal?.average ?? row.average,
        target: draft.target ?? savedGoal?.target ?? row.target,
      };
    }),
    [baseRows, drafts, savedGoals]
  );

  useEffect(() => {
    setLoading(true);
    setMessage("");
    api(`/education-goals/?year=${year}&include_inactive=true&page_size=1000`)
      .then((data) => setSavedGoals(data.results || data))
      .catch((err) => setMessage(err.message))
      .finally(() => setLoading(false));
  }, [year]);

  useEffect(() => {
    setDrafts({});
  }, [year]);

  const updateDraft = (key, field, value) => {
    setDrafts((current) => ({
      ...current,
      [key]: {
        ...(current[key] || {}),
        [field]: value,
      },
    }));
  };

  const saveGoals = async () => {
    setSaving(true);
    setMessage("");
    try {
      const saved = [];
      for (const row of rows) {
        const payload = {
          year: numberValue(year),
          key: row.key,
          label: row.label,
          average: numberValue(row.average),
          target: numberValue(row.target),
          order: row.order,
          is_active: true,
        };
        if (row.id) {
          saved.push(await api(`/education-goals/${row.id}/`, { method: "PUT", body: JSON.stringify(payload) }));
        } else {
          saved.push(await api("/education-goals/", { method: "POST", body: JSON.stringify(payload) }));
        }
      }
      setSavedGoals(saved);
      setDrafts({});
      setMessage(`Metas de ${year} salvas com sucesso.`);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  };

  const copyPreviousYear = async () => {
    setMessage("");
    try {
      const data = await api(`/education-goals/?year=${numberValue(year) - 1}&page_size=1000`);
      const previousGoals = data.results || data;
      if (!previousGoals.length) {
        setMessage(`Não há metas cadastradas para ${numberValue(year) - 1}.`);
        return;
      }
      setDrafts(Object.fromEntries(previousGoals.map((goal) => [
        goal.key,
        { average: goal.average, target: goal.target },
      ])));
      setMessage(`Metas de ${numberValue(year) - 1} copiadas para edição.`);
    } catch (err) {
      setMessage(err.message);
    }
  };

  return (
    <section className="page dashboard-page">
      <div className="page-title">
        <div>
          <h1>Metas</h1>
          <p>Cadastre as metas e médias usadas no quadro de estatísticas por ano.</p>
        </div>
        <div className="page-actions">
          <label className="filter-field compact-year">
            <span>Ano</span>
            <input type="number" min="2019" value={year} onChange={(event) => setYear(event.target.value)} />
          </label>
          <button className="secondary" type="button" onClick={copyPreviousYear}>Copiar ano anterior</button>
          <button type="button" onClick={saveGoals} disabled={saving || loading}><Save size={18} /> Salvar metas</button>
        </div>
      </div>

      {message && <div className="alert">{message}</div>}

      <div className="table-wrap goals-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Indicador</th>
              <th>Média histórica</th>
              <th>Meta {year}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className={row.section ? "goal-section-row" : ""} key={row.key}>
                <td>{row.label}</td>
                <td>
                  <input
                    min="0"
                    type="number"
                    value={row.average}
                    onChange={(event) => updateDraft(row.key, "average", event.target.value)}
                  />
                </td>
                <td>
                  <input
                    min="0"
                    type="number"
                    value={row.target}
                    onChange={(event) => updateDraft(row.key, "target", event.target.value)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
