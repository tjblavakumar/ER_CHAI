import React, { useEffect, useState, useRef } from 'react';
import { useAppStore } from '../store/appStore';
import {
  listProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  loadDatasetRows,
} from '../api/client';

// ---------------------------------------------------------------------------
// SaveDialog — inline modal for naming a project before save
// ---------------------------------------------------------------------------

interface SaveDialogProps {
  defaultName: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
}

const SaveDialog: React.FC<SaveDialogProps> = ({ defaultName, onConfirm, onCancel }) => {
  const [name, setName] = useState(defaultName);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleConfirm = () => {
    if (!name.trim()) {
      setError('A project name is required.');
      return;
    }
    onConfirm(name.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleConfirm();
    if (e.key === 'Escape') onCancel();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.35)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: '#fff',
          borderRadius: 8,
          padding: 20,
          minWidth: 320,
          boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 12 }}>Save Project</div>
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (error) setError('');
          }}
          onKeyDown={handleKeyDown}
          style={{
            width: '100%',
            padding: '6px 8px',
            fontSize: 13,
            border: error ? '1px solid #c00' : '1px solid #ccc',
            borderRadius: 4,
            boxSizing: 'border-box',
          }}
        />
        {error && (
          <div style={{ color: '#c00', fontSize: 12, marginTop: 4 }}>{error}</div>
        )}
        <div style={{ display: 'flex', gap: 8, marginTop: 14, justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{ fontSize: 13, padding: '5px 14px', cursor: 'pointer' }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            style={{
              fontSize: 13,
              padding: '5px 14px',
              cursor: 'pointer',
              background: '#1a73e8',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// ProjectList
// ---------------------------------------------------------------------------

const ProjectList: React.FC = () => {
  const projects = useAppStore((s) => s.projects);
  const setProjects = useAppStore((s) => s.setProjects);
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const setCurrentProjectId = useAppStore((s) => s.setCurrentProjectId);
  const currentProjectName = useAppStore((s) => s.currentProjectName);
  const setCurrentProjectName = useAppStore((s) => s.setCurrentProjectName);
  const chartState = useAppStore((s) => s.chartState);
  const setChartState = useAppStore((s) => s.setChartState);
  const setSummaryText = useAppStore((s) => s.setSummaryText);
  const setDatasetInfo = useAppStore((s) => s.setDatasetInfo);
  const setDatasetRows = useAppStore((s) => s.setDatasetRows);
  const summaryText = useAppStore((s) => s.summaryText);
  const resetForNewChart = useAppStore((s) => s.resetForNewChart);

  const [saving, setSaving] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);

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
      setCurrentProjectName(project.name);
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
        setCurrentProjectName(null);
      }
      await refreshProjects();
    } catch {
      // Error toast handled by API interceptor
    }
  };

  const handleSave = () => {
    if (!chartState) return;
    setShowSaveDialog(true);
  };

  const handleSaveConfirm = async (name: string) => {
    if (!chartState) return;
    setShowSaveDialog(false);
    setSaving(true);
    try {
      if (currentProjectId) {
        await updateProject(currentProjectId, {
          name,
          chart_state: chartState,
          summary_text: summaryText,
        });
      } else {
        const project = await createProject({
          name,
          chart_state: chartState,
          dataset_path: chartState.dataset_path,
          summary_text: summaryText,
        });
        setCurrentProjectId(project.id);
      }
      setCurrentProjectName(name);
      await refreshProjects();
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setSaving(false);
    }
  };

  const handleSaveCancel = () => {
    setShowSaveDialog(false);
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

  const defaultSaveName = currentProjectName ?? `Chart ${new Date().toLocaleString()}`;

  return (
    <div>
      {showSaveDialog && (
        <SaveDialog
          defaultName={defaultSaveName}
          onConfirm={handleSaveConfirm}
          onCancel={handleSaveCancel}
        />
      )}

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
