import React, { useState } from 'react';
import { useAppStore } from '../store/appStore';
import {
  exportPython,
  exportR,
  exportPdf,
  exportPythonDirect,
  exportRDirect,
  exportPdfDirect,
  exportPdfWithImage,
} from '../api/client';

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
  const chartState = useAppStore((s) => s.chartState);
  const summaryText = useAppStore((s) => s.summaryText);
  const [loading, setLoading] = useState<Record<ExportType, boolean>>({
    python: false,
    r: false,
    pdf: false,
  });

  const disabled = !currentProjectId && !chartState;

  const handleExport = async (type: ExportType) => {
    if (!currentProjectId && !chartState) return;
    setLoading((prev) => ({ ...prev, [type]: true }));
    try {
      let blob: Blob;
      let filename: string;
      switch (type) {
        case 'python':
          if (currentProjectId) {
            blob = await exportPython(currentProjectId);
          } else {
            blob = await exportPythonDirect(chartState!);
          }
          filename = 'chart_python.zip';
          break;
        case 'r':
          if (currentProjectId) {
            blob = await exportR(currentProjectId);
          } else {
            blob = await exportRDirect(chartState!);
          }
          filename = 'chart_r.zip';
          break;
        case 'pdf': {
          const summaryForPdf = summaryText || 'No summary available.';
          const canvas = document.querySelector('.konvajs-content canvas') as HTMLCanvasElement;
          if (canvas) {
            const dataUrl = canvas.toDataURL('image/png');
            const response = await fetch(dataUrl);
            const imageBlob = await response.blob();
            blob = await exportPdfWithImage(imageBlob, summaryForPdf);
          } else if (currentProjectId) {
            blob = await exportPdf(currentProjectId);
          } else {
            blob = await exportPdfDirect(chartState!, summaryForPdf);
          }
          filename = 'chart.pdf';
          break;
        }
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
        title={disabled ? 'Load a chart to enable export' : 'Export as Python zip'}
      >
        {loading.python ? 'Exporting…' : 'Python'}
      </button>
      <button
        onClick={() => handleExport('r')}
        disabled={disabled || loading.r}
        style={buttonStyle(loading.r)}
        title={disabled ? 'Load a chart to enable export' : 'Export as R zip'}
      >
        {loading.r ? 'Exporting…' : 'R'}
      </button>
      <button
        onClick={() => handleExport('pdf')}
        disabled={disabled || loading.pdf}
        style={buttonStyle(loading.pdf)}
        title={disabled ? 'Load a chart to enable export' : 'Export as PDF'}
      >
        {loading.pdf ? 'Exporting…' : 'PDF'}
      </button>
    </div>
  );
};

export default ExportToolbar;
