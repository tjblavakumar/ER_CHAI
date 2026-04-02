import React from 'react';
import { Group, Rect, Text, Line } from 'react-konva';
import type { AnnotationConfig } from '../../types';

interface AnnotationElementProps {
  config: AnnotationConfig;
  chartArea: { x: number; y: number; width: number; height: number };
  yMin?: number;
  yMax?: number;
  xLabels?: string[];
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

function dashForStyle(style: string): number[] | undefined {
  switch (style) {
    case 'dashed': return [8, 4];
    case 'dotted': return [3, 3];
    default: return undefined;
  }
}

/**
 * Find the fractional x-position (0..1) for a date string within the xLabels array.
 * Matches by prefix (e.g., "2020-01" matches "2020-01-01").
 */
function dateToFraction(dateStr: string, xLabels: string[]): number | null {
  if (!dateStr || xLabels.length === 0) return null;
  const needle = dateStr.trim();

  // Direct prefix match
  let idx = xLabels.findIndex((lbl) => lbl.startsWith(needle) || needle.startsWith(lbl));
  if (idx >= 0) return idx / Math.max(xLabels.length - 1, 1);

  // If needle is a pure year number (e.g., "2008"), try "2008-01"
  if (/^\d{4}(\.\d+)?$/.test(needle)) {
    const year = Math.floor(Number(needle));
    const frac = Number(needle) - year; // e.g., 2001.75 -> 0.75
    const month = Math.round(frac * 12) + 1;
    const datePrefix = `${year}-${String(month).padStart(2, '0')}`;
    idx = xLabels.findIndex((lbl) => lbl.startsWith(datePrefix));
    if (idx >= 0) return idx / Math.max(xLabels.length - 1, 1);
    // Try just the year
    idx = xLabels.findIndex((lbl) => lbl.startsWith(String(year)));
    if (idx >= 0) return idx / Math.max(xLabels.length - 1, 1);
  }

  // Try parsing as date and finding closest
  let target = new Date(needle).getTime();
  if (isNaN(target) && /^\d{4}$/.test(needle)) {
    target = new Date(`${needle}-01-01`).getTime();
  }
  if (isNaN(target)) return null;

  let bestIdx = 0;
  let bestDist = Infinity;
  for (let i = 0; i < xLabels.length; i++) {
    const t = new Date(xLabels[i]).getTime();
    if (!isNaN(t)) {
      const dist = Math.abs(t - target);
      if (dist < bestDist) { bestDist = dist; bestIdx = i; }
    }
  }
  return bestIdx / Math.max(xLabels.length - 1, 1);
}

const AnnotationElement: React.FC<AnnotationElementProps> = ({
  config,
  chartArea,
  yMin = 0,
  yMax = 100,
  xLabels,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  const elementId = `annotation_${config.id}`;

  const handleContextMenu = (e: import('konva/lib/Node').KonvaEventObject<MouseEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    if (stage) {
      const pointer = stage.getPointerPosition();
      if (pointer) onContextMenu?.(elementId, pointer.x, pointer.y);
    }
  };

  // Horizontal line at a specific Y value
  if (config.type === 'horizontal_line') {
    const lineVal = config.line_value ?? 0;
    const yRange = yMax - yMin || 1;
    const py = chartArea.y + chartArea.height - ((lineVal - yMin) / yRange) * chartArea.height;
    const dash = dashForStyle(config.line_style ?? 'dotted');
    const label = config.text ?? `${lineVal}`;

    return (
      <Group
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.(elementId, e.target.x(), e.target.y())}
      >
        <Line
          points={[chartArea.x, py, chartArea.x + chartArea.width, py]}
          stroke={config.line_color ?? '#cc0000'}
          strokeWidth={config.line_width ?? 1.5}
          dash={dash}
        />
        {label && (
          <Text
            x={chartArea.x + chartArea.width + 4}
            y={py - 6}
            text={label}
            fontSize={config.font_size}
            fontFamily="Arial"
            fill={config.line_color ?? '#cc0000'}
          />
        )}
      </Group>
    );
  }

  // Vertical line at a specific x-axis date/value position
  if (config.type === 'vertical_line') {
    const dash = dashForStyle(config.line_style ?? 'solid');
    const label = config.text ?? '';

    // Try to find x position from line_value as a date or from xLabels
    let px = config.position.x;
    if (xLabels && xLabels.length > 0 && config.line_value != null) {
      // line_value might be a year like 2008 or a date string
      const valStr = String(config.line_value);
      const frac = dateToFraction(valStr, xLabels);
      if (frac != null) {
        px = chartArea.x + frac * chartArea.width;
      }
    }

    return (
      <Group
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.(elementId, e.target.x(), e.target.y())}
      >
        <Line
          points={[px, chartArea.y, px, chartArea.y + chartArea.height]}
          stroke={config.line_color ?? '#cc0000'}
          strokeWidth={config.line_width ?? 1.5}
          dash={dash}
        />
        {label && (
          <Text
            x={px + 8}
            y={chartArea.y + 2}
            text={label}
            fontSize={config.font_size}
            fontFamily="Arial"
            fill={config.line_color ?? '#cc0000'}
            rotation={90}
          />
        )}
      </Group>
    );
  }

  // Vertical band — position from band_start/band_end dates when xLabels available
  if (config.type === 'vertical_band') {
    let bandX = config.position.x;
    let bandWidth = chartArea.width * 0.15;

    if (xLabels && xLabels.length > 0 && config.band_start) {
      const startFrac = dateToFraction(config.band_start, xLabels);
      const endFrac = config.band_end
        ? dateToFraction(config.band_end, xLabels)
        : startFrac != null ? Math.min(startFrac + 0.05, 1) : null;

      if (startFrac != null && endFrac != null) {
        bandX = chartArea.x + startFrac * chartArea.width;
        bandWidth = Math.max((endFrac - startFrac) * chartArea.width, 4);
      }
    }

    return (
      <Group
        x={bandX}
        y={chartArea.y}
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.(elementId, e.target.x(), e.target.y())}
      >
        <Rect
          width={bandWidth}
          height={chartArea.height}
          fill={config.band_color ?? '#cccccc'}
          opacity={0.3}
        />
      </Group>
    );
  }

  // Text annotation
  return (
    <Group
      x={config.position.x}
      y={config.position.y}
      draggable={draggable}
      onDragEnd={(e) => onDragEnd?.(elementId, e.target.x(), e.target.y())}
      onContextMenu={handleContextMenu}
    >
      <Text
        text={config.text ?? ''}
        fontSize={config.font_size}
        fontFamily="Arial"
        fill={config.font_color}
      />
    </Group>
  );
};

export default AnnotationElement;
