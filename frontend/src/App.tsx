import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useAppStore } from './store/appStore';
import { ingestFromUrl, ingestFromFile, generateSummary, reanalyzeChart } from './api/client';
import type { ChartContext } from './types';

import ProjectList from './components/ProjectList';
import CanvasEditor from './components/CanvasEditor';
import ControlsPanel from './components/ControlsPanel';
import SummaryEditor from './components/SummaryEditor';
import ExportToolbar from './components/ExportToolbar';
import AIChatWindow from './components/AIChatWindow';
import ChartPreviewOverlay from './components/ChartPreviewOverlay';
import { generateChartVariants } from './utils/chartVariants';

// ---------------------------------------------------------------------------
// Resizable divider hook
// ---------------------------------------------------------------------------

function useResizable(
  direction: 'horizontal' | 'vertical',
  initial: number,
  min: number,
  max: number,
) {
  const [size, setSize] = useState(initial);
  const dragging = useRef(false);
  const startPos = useRef(0);
  const startSize = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startPos.current = direction === 'horizontal' ? e.clientX : e.clientY;
      startSize.current = size;

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        const delta =
          direction === 'horizontal'
            ? ev.clientX - startPos.current
            : ev.clientY - startPos.current;
        const newSize = Math.min(max, Math.max(min, startSize.current + delta));
        setSize(newSize);
      };

      const onMouseUp = () => {
        dragging.current = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
      document.body.style.userSelect = 'none';
    },
    [direction, size, min, max],
  );

  return { size, onMouseDown };
}

// Divider for right sidebar (drag changes width, but we drag from the left edge)
function useResizableRight(
  initial: number,
  min: number,
  max: number,
) {
  const [size, setSize] = useState(initial);
  const dragging = useRef(false);
  const startPos = useRef(0);
  const startSize = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startPos.current = e.clientX;
      startSize.current = size;

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        // Dragging left increases width, dragging right decreases
        const delta = startPos.current - ev.clientX;
        const newSize = Math.min(max, Math.max(min, startSize.current + delta));
        setSize(newSize);
      };

      const onMouseUp = () => {
        dragging.current = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [size, min, max],
  );

  return { size, onMouseDown };
}

// Divider for bottom section (drag changes height, dragging up increases)
function useResizableBottom(
  initial: number,
  min: number,
  max: number,
) {
  const [size, setSize] = useState(initial);
  const dragging = useRef(false);
  const startPos = useRef(0);
  const startSize = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startPos.current = e.clientY;
      startSize.current = size;

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        const delta = startPos.current - ev.clientY;
        const newSize = Math.min(max, Math.max(min, startSize.current + delta));
        setSize(newSize);
      };

      const onMouseUp = () => {
        dragging.current = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      document.body.style.cursor = 'row-resize';
      document.body.style.userSelect = 'none';
    },
    [size, min, max],
  );

  return { size, onMouseDown };
}

// ---------------------------------------------------------------------------
// Divider component
// ---------------------------------------------------------------------------

const dividerBaseStyle: React.CSSProperties = {
  flexShrink: 0,
  background: '#e0e0e0',
  transition: 'background 0.15s',
  zIndex: 10,
};

const DividerH: React.FC<{ onMouseDown: (e: React.MouseEvent) => void }> = ({ onMouseDown }) => (
  <div
    onMouseDown={onMouseDown}
    style={{
      ...dividerBaseStyle,
      width: 5,
      cursor: 'col-resize',
      alignSelf: 'stretch',
    }}
    onMouseEnter={(e) => (e.currentTarget.style.background = '#1a73e8')}
    onMouseLeave={(e) => (e.currentTarget.style.background = '#e0e0e0')}
  />
);

const DividerV: React.FC<{ onMouseDown: (e: React.MouseEvent) => void }> = ({ onMouseDown }) => (
  <div
    onMouseDown={onMouseDown}
    style={{
      ...dividerBaseStyle,
      height: 5,
      cursor: 'row-resize',
      width: '100%',
    }}
    onMouseEnter={(e) => (e.currentTarget.style.background = '#1a73e8')}
    onMouseLeave={(e) => (e.currentTarget.style.background = '#e0e0e0')}
  />
);

// ---------------------------------------------------------------------------
// Network error banner — polls /api/health to detect connectivity (Req 2.5)
// ---------------------------------------------------------------------------

const NetworkBanner: React.FC = () => {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        await fetch('/api/health', { method: 'GET', cache: 'no-store' });
        if (mounted) setOffline(false);
      } catch {
        if (mounted) setOffline(true);
      }
    };

    check();
    const id = setInterval(check, 10_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="alert"
      style={{
        background: '#d32f2f',
        color: '#fff',
        textAlign: 'center',
        padding: '6px 12px',
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      Unable to reach the server. Please check your connection.
    </div>
  );
};

// ---------------------------------------------------------------------------
// Data Ingestion Bar (Req 3.1, 3.2, 3.3, 4.1, 4.2, 4.5, 5.5, 12.1)
// ---------------------------------------------------------------------------

const DataIngestionBar: React.FC = () => {
  const setChartState = useAppStore((s) => s.setChartState);
  const setDatasetInfo = useAppStore((s) => s.setDatasetInfo);
  const setDatasetRows = useAppStore((s) => s.setDatasetRows);
  const setIsLoading = useAppStore((s) => s.setIsLoading);
  const setLoadingMessage = useAppStore((s) => s.setLoadingMessage);
  const setReferenceImageFile = useAppStore((s) => s.setReferenceImageFile);
  const setPreviewVariants = useAppStore((s) => s.setPreviewVariants);
  const isLoading = useAppStore((s) => s.isLoading);

  const [fredUrl, setFredUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const fredImageInputRef = useRef<HTMLInputElement>(null);

  // FRED URL ingestion flow (with optional reference image)
  const handleFredIngest = useCallback(async () => {
    const url = fredUrl.trim();
    if (!url) return;
    const refImage = fredImageInputRef.current?.files?.[0];
    if (refImage) {
      setReferenceImageFile(refImage);
    } else {
      setReferenceImageFile(null);
    }
    setIsLoading(true);
    try {
      setLoadingMessage(
        refImage
          ? 'Downloading data from FRED & analyzing reference image...'
          : 'Downloading data from FRED...',
      );
      const result = await ingestFromUrl(url, refImage);
      setLoadingMessage('Generating chart previews...');
      // Generate variants and show preview overlay
      const variants = generateChartVariants(result.chart_state);
      setPreviewVariants(variants, result.dataset_rows ?? null, result.dataset_info);
      setFredUrl('');
      if (fredImageInputRef.current) fredImageInputRef.current.value = '';
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [fredUrl, setChartState, setDatasetInfo, setIsLoading, setLoadingMessage, setDatasetRows, setReferenceImageFile]);

  // File upload ingestion flow
  const handleFileUpload = useCallback(async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    const refImage = imageInputRef.current?.files?.[0];
    // Store reference image in app store before ingestion
    if (refImage) {
      setReferenceImageFile(refImage);
    } else {
      setReferenceImageFile(null);
    }
    setIsLoading(true);
    try {
      setLoadingMessage(refImage
        ? 'Parsing data and analyzing reference image (this may take a moment)...'
        : 'Parsing data and generating chart...');
      const result = await ingestFromFile(file, refImage);
      setLoadingMessage('Generating chart previews...');
      // Generate variants — if reference image was provided, the result already has reference styling
      const baseState = result.chart_state;
      const variants = generateChartVariants(baseState, refImage ? baseState : null);
      setPreviewVariants(variants, result.dataset_rows ?? null, result.dataset_info);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (imageInputRef.current) imageInputRef.current.value = '';
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [setChartState, setDatasetInfo, setIsLoading, setLoadingMessage, setReferenceImageFile, setDatasetRows]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleFredIngest();
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'stretch',
        gap: 10,
        padding: '8px 16px',
        borderBottom: '1px solid #e0e0e0',
        background: '#f5f7fa',
        flexWrap: 'wrap',
        fontSize: 13,
      }}
    >
      {/* ---- FRED URL section (blue tint) ---- */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 12px',
          background: '#e8f0fe',
          border: '1px solid #c5d7f2',
          borderRadius: 6,
          flexWrap: 'wrap',
        }}
      >
        <label htmlFor="fred-url" style={{ fontWeight: 600, whiteSpace: 'nowrap', color: '#1a56db' }}>
          FRED URL:
        </label>
        <input
          id="fred-url"
          type="text"
          value={fredUrl}
          onChange={(e) => setFredUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://fred.stlouisfed.org/series/..."
          disabled={isLoading}
          style={{
            width: 250,
            padding: '4px 8px',
            border: '1px solid #a4c2f4',
            borderRadius: 4,
            fontSize: 12,
            background: '#fff',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <label htmlFor="fred-ref-image" style={{ fontWeight: 500, whiteSpace: 'nowrap', fontSize: 11, color: '#5a7dba' }}>
            Ref image:
          </label>
          <input
            id="fred-ref-image"
            ref={fredImageInputRef}
            type="file"
            accept="image/*"
            disabled={isLoading}
            style={{ fontSize: 11, maxWidth: 150 }}
          />
        </div>
        <button
          onClick={handleFredIngest}
          disabled={isLoading || !fredUrl.trim()}
          style={{
            padding: '4px 14px',
            fontSize: 12,
            cursor: isLoading || !fredUrl.trim() ? 'not-allowed' : 'pointer',
            opacity: isLoading || !fredUrl.trim() ? 0.6 : 1,
            background: '#1a73e8',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            fontWeight: 600,
          }}
        >
          {isLoading ? 'Loading…' : 'Generate'}
        </button>
      </div>

      {/* ---- CSV/Excel upload section (green tint) ---- */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 12px',
          background: '#e6f4ea',
          border: '1px solid #b7dfc3',
          borderRadius: 6,
          flexWrap: 'wrap',
        }}
      >
        <label htmlFor="data-file" style={{ fontWeight: 600, whiteSpace: 'nowrap', color: '#1e7e34' }}>
          Upload CSV/Excel:
        </label>
        <input
          id="data-file"
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          disabled={isLoading}
          style={{ fontSize: 12 }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <label htmlFor="ref-image" style={{ fontWeight: 600, whiteSpace: 'nowrap', fontSize: 11, color: '#3d8b5e' }}>
            Reference image:
          </label>
          <input
            id="ref-image"
            ref={imageInputRef}
            type="file"
            accept="image/*"
            disabled={isLoading}
            style={{ fontSize: 12 }}
          />
        </div>
        <button
          onClick={handleFileUpload}
          disabled={isLoading}
          style={{
            padding: '4px 14px',
            fontSize: 12,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1,
            background: '#1e8e3e',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            fontWeight: 600,
          }}
        >
          {isLoading ? 'Uploading…' : 'Generate'}
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Bedrock Status Indicator
// ---------------------------------------------------------------------------

const BedrockStatus: React.FC = () => {
  const [status, setStatus] = useState<{ active: boolean; model: string; error: string } | null>(null);

  useEffect(() => {
    fetch('/api/bedrock/status')
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus({ active: false, model: '', error: 'Unable to check' }));
  }, []);

  if (!status) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        color: status.active ? '#2e7d32' : '#c62828',
        padding: '2px 8px',
        borderRadius: 4,
        background: status.active ? '#e8f5e9' : '#ffebee',
      }}
      title={status.active ? `Model: ${status.model}` : `Error: ${status.error}`}
    >
      <span style={{ fontSize: 8 }}>{status.active ? '●' : '●'}</span>
      {status.active ? 'Bedrock Active' : 'Bedrock Offline'}
    </div>
  );
};

// ---------------------------------------------------------------------------
// App Shell (Req 6.1, 9.1, 10.1, 12.4, 2.5)
// ---------------------------------------------------------------------------

const App: React.FC = () => {
  const isLoading = useAppStore((s) => s.isLoading);
  const loadingMessage = useAppStore((s) => s.loadingMessage);
  const chartState = useAppStore((s) => s.chartState);
  const referenceImageFile = useAppStore((s) => s.referenceImageFile);
  const setChartState = useAppStore((s) => s.setChartState);
  const setDatasetInfo = useAppStore((s) => s.setDatasetInfo);
  const setDatasetRows = useAppStore((s) => s.setDatasetRows);
  const setIsLoading = useAppStore((s) => s.setIsLoading);
  const setLoadingMessage = useAppStore((s) => s.setLoadingMessage);
  const setSummaryText = useAppStore((s) => s.setSummaryText);

  // Chart preview overlay
  const previewVariants = useAppStore((s) => s.previewVariants);
  const previewDatasetRows = useAppStore((s) => s.previewDatasetRows);
  const previewDatasetInfo = useAppStore((s) => s.previewDatasetInfo);
  const showPreviewOverlay = useAppStore((s) => s.showPreviewOverlay);
  const setShowPreviewOverlay = useAppStore((s) => s.setShowPreviewOverlay);

  const handlePreviewSelect = useCallback((selectedState: import('./types').ChartState) => {
    setChartState(selectedState);
    setDatasetRows(previewDatasetRows);
    if (previewDatasetInfo) setDatasetInfo(previewDatasetInfo);
    setShowPreviewOverlay(false);
  }, [setChartState, setDatasetRows, setDatasetInfo, previewDatasetRows, previewDatasetInfo, setShowPreviewOverlay]);

  const handlePreviewCancel = useCallback(() => {
    setShowPreviewOverlay(false);
  }, [setShowPreviewOverlay]);

  // Resizable panels
  const leftSidebar = useResizable('horizontal', 220, 150, 400);
  const rightSidebar = useResizableRight(270, 200, 500);
  const summaryPanel = useResizableBottom(250, 120, 600);

  const handleReanalyze = useCallback(async () => {
    if (!chartState || !referenceImageFile) return;
    setIsLoading(true);
    try {
      setLoadingMessage('Re-analyzing reference image...');
      const result = await reanalyzeChart(referenceImageFile, chartState.dataset_path);
      setLoadingMessage('Rendering chart...');
      setChartState(result.chart_state);
      setDatasetRows(result.dataset_rows ?? null);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [chartState, referenceImageFile, setChartState, setDatasetRows, setIsLoading, setLoadingMessage]);

  const handleGenerateSummary = useCallback(async () => {
    if (!chartState) return;
    setIsLoading(true);
    try {
      setLoadingMessage('Generating executive summary...');
      const context: ChartContext = {
        chart_state: chartState,
        dataset_summary: '',
        dataset_sample: [],
      };
      const summary = await generateSummary(chartState.dataset_path, context);
      setSummaryText(summary);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [chartState, setIsLoading, setLoadingMessage, setSummaryText]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'Arial, sans-serif', position: 'relative' }}>
      {/* Persistent network error banner */}
      <NetworkBanner />

      {/* Full-screen loading overlay */}
      {isLoading && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.45)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              padding: '32px 48px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
              textAlign: 'center',
              maxWidth: 400,
            }}
          >
            {/* Spinner */}
            <div
              style={{
                width: 40,
                height: 40,
                border: '4px solid #e0e0e0',
                borderTopColor: '#1a73e8',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
                margin: '0 auto 16px',
              }}
            />
            <div style={{ fontSize: 15, fontWeight: 600, color: '#333', marginBottom: 6 }}>
              {loadingMessage || 'Processing...'}
            </div>
            <div style={{ fontSize: 12, color: '#888' }}>Please wait</div>
          </div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left sidebar — Project List */}
        <aside
          style={{
            width: leftSidebar.size,
            minWidth: 150,
            borderRight: '1px solid #ddd',
            padding: 12,
            overflowY: 'auto',
            background: '#f9f9f9',
            flexShrink: 0,
          }}
        >
          <h2 style={{ fontSize: 15, margin: '0 0 10px' }}>Projects</h2>
          <ProjectList />
        </aside>

        {/* Left divider */}
        <DividerH onMouseDown={leftSidebar.onMouseDown} />

        {/* Main content area */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          {/* Header: title + export toolbar */}
          <header
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 16px',
              borderBottom: '1px solid #ddd',
              background: '#fff',
              flexShrink: 0,
            }}
          >
            <h1 style={{ fontSize: 18, margin: 0, display: 'flex', alignItems: 'baseline', gap: 8 }}>
              CHAI : Chart AI Assistant
              <span style={{ fontSize: 11, fontWeight: 400, color: '#888', fontStyle: 'italic' }}>v3.2</span>
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  onClick={handleReanalyze}
                  disabled={!chartState || !referenceImageFile || isLoading}
                  style={{
                    padding: '4px 12px',
                    fontSize: 12,
                    cursor: !chartState || !referenceImageFile || isLoading ? 'not-allowed' : 'pointer',
                    opacity: !chartState || !referenceImageFile || isLoading ? 0.6 : 1,
                  }}
                >
                  Reanalyze &amp; Regenerate
                </button>
                <button
                  onClick={handleGenerateSummary}
                  disabled={!chartState || isLoading}
                  style={{
                    padding: '4px 12px',
                    fontSize: 12,
                    cursor: !chartState || isLoading ? 'not-allowed' : 'pointer',
                    opacity: !chartState || isLoading ? 0.6 : 1,
                  }}
                >
                  Exe Summary
                </button>
              </div>
              <BedrockStatus />
              <ExportToolbar />
            </div>
          </header>

          {/* Data ingestion bar */}
          <DataIngestionBar />

          {/* Canvas + Controls + Summary */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Canvas + Controls row */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 200 }}>
              {/* Center: Canvas Editor */}
              <section
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#f0f0f0',
                  overflow: 'auto',
                  minWidth: 400,
                }}
              >
                <CanvasEditor />
              </section>

              {/* Right divider */}
              <DividerH onMouseDown={rightSidebar.onMouseDown} />

              {/* Right sidebar: Controls Panel */}
              <aside
                style={{
                  width: rightSidebar.size,
                  minWidth: 200,
                  borderLeft: '1px solid #ddd',
                  padding: 12,
                  overflowY: 'auto',
                  background: '#fafafa',
                  flexShrink: 0,
                }}
              >
                <h2 style={{ fontSize: 15, margin: '0 0 10px' }}>Controls</h2>
                <ControlsPanel />
              </aside>
            </div>

            {/* Bottom divider */}
            <DividerV onMouseDown={summaryPanel.onMouseDown} />

            {/* Bottom: Summary Editor */}
            <section
              style={{
                height: summaryPanel.size,
                minHeight: 120,
                borderTop: '1px solid #ddd',
                padding: 12,
                background: '#fff',
                flexShrink: 0,
                overflowY: 'auto',
              }}
            >
              <SummaryEditor />
            </section>
          </div>
        </main>
      </div>

      {/* Floating overlay: AI Chat Window */}
      <AIChatWindow />

      {/* Chart preview overlay */}
      {showPreviewOverlay && previewVariants.length > 0 && (
        <ChartPreviewOverlay
          variants={previewVariants}
          datasetRows={previewDatasetRows}
          onSelect={handlePreviewSelect}
          onCancel={handlePreviewCancel}
        />
      )}
    </div>
  );
};

export default App;
