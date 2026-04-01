import React, { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import type { ChartState, ChartElementState } from '../types';

const FONT_SIZES = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32];
const FONT_COLORS = [
  '#000000', '#333333', '#666666', '#999999',
  '#003366', '#006699', '#0099cc', '#cc0000',
  '#cc6600', '#339933', '#663399', '#ffffff',
];
const FONT_FAMILIES = ['Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Courier New', 'Verdana'];

interface ContextMenuProps {
  onApplyChange: (elementId: string, property: string, value: string | number) => void;
}

const ContextMenu: React.FC<ContextMenuProps> = ({ onApplyChange }) => {
  const contextMenuTarget = useAppStore((s) => s.contextMenuTarget);
  const setContextMenuTarget = useAppStore((s) => s.setContextMenuTarget);
  const chartState = useAppStore((s) => s.chartState);
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setContextMenuTarget(null), [setContextMenuTarget]);

  // Close on outside click
  useEffect(() => {
    if (!contextMenuTarget) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        close();
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [contextMenuTarget, close]);

  // Close on Escape
  useEffect(() => {
    if (!contextMenuTarget) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [contextMenuTarget, close]);

  if (!contextMenuTarget || !chartState) return null;

  const currentElement = resolveElement(chartState, contextMenuTarget.elementId);

  return (
    <div
      ref={menuRef}
      style={{
        position: 'absolute',
        left: contextMenuTarget.x,
        top: contextMenuTarget.y,
        background: '#fff',
        border: '1px solid #ccc',
        borderRadius: 6,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        padding: 12,
        zIndex: 1000,
        minWidth: 200,
        fontSize: 13,
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#333' }}>
        Text Properties
      </div>

      {/* Font Size */}
      <div style={{ marginBottom: 8 }}>
        <label style={labelStyle}>Font Size</label>
        <select
          value={currentElement?.font_size ?? 14}
          onChange={(e) =>
            onApplyChange(contextMenuTarget.elementId, 'font_size', Number(e.target.value))
          }
          style={selectStyle}
        >
          {FONT_SIZES.map((s) => (
            <option key={s} value={s}>{s}px</option>
          ))}
        </select>
      </div>

      {/* Font Color */}
      <div style={{ marginBottom: 8 }}>
        <label style={labelStyle}>Font Color</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {FONT_COLORS.map((c) => (
            <div
              key={c}
              onClick={() => onApplyChange(contextMenuTarget.elementId, 'font_color', c)}
              style={{
                width: 20,
                height: 20,
                background: c,
                border: c === (currentElement?.font_color ?? '#000000')
                  ? '2px solid #0066cc'
                  : '1px solid #ccc',
                borderRadius: 3,
                cursor: 'pointer',
              }}
            />
          ))}
        </div>
      </div>

      {/* Font Family */}
      <div>
        <label style={labelStyle}>Font Family</label>
        <select
          value={currentElement?.font_family ?? 'Arial'}
          onChange={(e) =>
            onApplyChange(contextMenuTarget.elementId, 'font_family', e.target.value)
          }
          style={selectStyle}
        >
          {FONT_FAMILIES.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
      </div>
    </div>
  );
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: 4,
  color: '#666',
  fontSize: 11,
};

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '4px 6px',
  border: '1px solid #ccc',
  borderRadius: 4,
  fontSize: 13,
};

/**
 * Resolve the current font properties for a given element ID from the chart state.
 */
function resolveElement(
  chartState: ChartState,
  elementId: string,
): Pick<ChartElementState, 'font_size' | 'font_color' | 'font_family'> | null {
  if (elementId === 'title') {
    return chartState.title;
  }
  if (elementId === 'x_label' || elementId === 'y_label') {
    return { font_size: 12, font_color: '#333', font_family: 'Arial' };
  }
  if (elementId === 'legend') {
    return { font_size: 11, font_color: '#333', font_family: 'Arial' };
  }
  if (elementId === 'data_table') {
    return {
      font_size: chartState.data_table?.font_size ?? 10,
      font_color: '#333',
      font_family: 'Arial',
    };
  }
  if (elementId.startsWith('annotation_')) {
    const annId = elementId.replace('annotation_', '');
    const ann = chartState.annotations.find((a) => a.id === annId);
    if (ann) {
      return { font_size: ann.font_size, font_color: ann.font_color, font_family: 'Arial' };
    }
  }
  return null;
}

export default ContextMenu;
