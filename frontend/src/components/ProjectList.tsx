import React, { useEffect, useState } from 'react';
import { useAppStore } from '../store/appStore';
import {
  listProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  loadDatasetRows,
} from '../api/client';

const ProjectList: React.FC = () => {
  const projects = useAppStore((s) => s.projects);
  const setProjects = useAppStore((s) => s.setProjects);
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const setCurrentProjectId = useAppStore((s) => s.setCurrentProjectId);
  const chartState = useAppStore((s) => s.chartState);
  const setChartState = useAppStore((s) => s.setChartState);
  const setSummaryText = useAppStore((s) => s.setSummaryText);
  const setDatasetInfo = useAppStore((s) => s.setDatasetInfo);
  const setDatasetRows = useAppStore((s) => s.setDatasetRows);
  const summaryText = useAppStore((s) => s.summaryText);
  const resetForNewChart = useAppStore((s) => s.resetForNewChart);

  const [saving, setSaving] = useState(false);

  const refreshProjects = async () => {
    try {
      const list = await listProjects();
      setProjects(list);
    } catch {
      // Error toast handled by API interceptor
    }
  };

  useEffect(() => {
    refreshProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLoad = async (id: string) => {
    try {
      const project = await getProject(id);
      setChartState(project.chart_state);
      setSummaryText(project.summary_text);
      setCurrentProjectId(project.id);
      setDatasetInfo(null);
      // Reload dataset rows from the saved CSV
      try {
        const rows = await loadDatasetRows(project.dataset_path);
        setDatasetRows(rows);
      } catch {
        setDatasetRows(null);
      }
    } catch {
      // Error toast handled by API interceptor
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteProject(id);
      if (currentProjectId === id) {
        setCurrentProjectId(null);
      }
      await refreshProjects();
    } catch {
      // Error toast handled by API interceptor
    }
  };

  const handleSave = async () => {
    if (!chartState) return;
    setSaving(true);
    try {
      if (currentProjectId) {
        await updateProject(currentProjectId, {
          chart_state: chartState,
          summary_text: summaryText,
        });
      } else {
        const name = `Chart ${new Date().toLocaleString()}`;
        const project = await createProject({
          name,
          chart_state: chartState,
          dataset_path: chartState.dataset_path,
          summary_text: summaryText,
        });
        setCurrentProjectId(project.id);
      }
      await refreshProjects();
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setSaving(false);
    }
  };

  const handleNewChart = () => {
    resetForNewChart();
    setCurrentProjectId(null);
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        <button
          onClick={handleSave}
          disabled={saving || !chartState}
          style={{
            flex: 1,
            fontSize: 12,
            padding: '4px 0',
            cursor: saving || !chartState ? 'not-allowed' : 'pointer',
          }}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          onClick={handleNewChart}
          style={{ flex: 1, fontSize: 12, padding: '4px 0', cursor: 'pointer' }}
        >
          New Chart
        </button>
      </div>

      {projects.length === 0 && (
        <p style={{ color: '#888', fontSize: 13 }}>No projects yet.</p>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {projects.map((p) => (
          <li
            key={p.id}
            style={{
              padding: '6px 4px',
              borderBottom: '1px solid #eee',
              background: p.id === currentProjectId ? '#e8f0fe' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div onClick={() => handleLoad(p.id)} style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {p.name}
              </div>
              <div style={{ fontSize: 11, color: '#888' }}>{formatDate(p.updated_at)}</div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(p.id);
              }}
              title="Delete project"
              style={{
                background: 'none',
                border: 'none',
                color: '#c00',
                cursor: 'pointer',
                fontSize: 14,
                padding: '0 4px',
                flexShrink: 0,
              }}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ProjectList;
