import React, { useState } from 'react';
import { useAppStore } from '../store/appStore';
import { exportPython, exportR, exportPdf } from '../api/client';

type ExportType = 'python' | 'r' | 'pdf';

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const ExportToolbar: React.FC = () => {
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const [loading, setLoading] = useState<Record<ExportType, boolean>>({
    python: false,
    r: false,
    pdf: false,
  });

  const disabled = !currentProjectId;

  const handleExport = async (type: ExportType) => {
    if (!currentProjectId) return;
    setLoading((prev) => ({ ...prev, [type]: true }));
    try {
      let blob: Blob;
      let filename: string;
      switch (type) {
        case 'python':
          blob = await exportPython(currentProjectId);
          filename = 'chart_python.zip';
          break;
        case 'r':
          blob = await exportR(currentProjectId);
          filename = 'chart_r.zip';
          break;
        case 'pdf':
          blob = await exportPdf(currentProjectId);
          filename = 'chart.pdf';
          break;
      }
      triggerDownload(blob, filename);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setLoading((prev) => ({ ...prev, [type]: false }));
    }
  };

  const buttonStyle = (isLoading: boolean): React.CSSProperties => ({
    fontSize: 12,
    padding: '4px 12px',
    cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
    opacity: disabled || isLoading ? 0.6 : 1,
  });

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 13, fontWeight: 600 }}>Export:</span>
      <button
        onClick={() => handleExport('python')}
        disabled={disabled || loading.python}
        style={buttonStyle(loading.python)}
        title={disabled ? 'Save the project first to enable export' : 'Export as Python zip'}
      >
        {loading.python ? 'Exporting…' : 'Python'}
      </button>
      <button
        onClick={() => handleExport('r')}
        disabled={disabled || loading.r}
        style={buttonStyle(loading.r)}
        title={disabled ? 'Save the project first to enable export' : 'Export as R zip'}
      >
        {loading.r ? 'Exporting…' : 'R'}
      </button>
      <button
        onClick={() => handleExport('pdf')}
        disabled={disabled || loading.pdf}
        style={buttonStyle(loading.pdf)}
        title={disabled ? 'Save the project first to enable export' : 'Export as PDF'}
      >
        {loading.pdf ? 'Exporting…' : 'PDF'}
      </button>
    </div>
  );
};

export default ExportToolbar;
