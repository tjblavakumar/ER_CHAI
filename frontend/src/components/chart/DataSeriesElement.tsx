import React from 'react';
import { Group, Line, Rect, Text } from 'react-konva';
import type { SeriesConfig } from '../../types';

interface DataSeriesElementProps {
  series: SeriesConfig[];
  chartArea: { x: number; y: number; width: number; height: number };
  yMin: number;
  yMax: number;
  datasetRows?: Record<string, unknown>[] | null;
  barGrouping?: string;
  categoryColumn?: string | null;
  groupColumn?: string | null;
  barLabelFontSize?: number;
  barStacking?: string;  // "grouped" | "stacked"
  onContextMenu?: (elementId: string, x: number, y: number) => void;
}

/**
 * Extract numeric values for a series column from dataset rows.
 */
function extractSeriesData(
  rows: Record<string, unknown>[],
  column: string,
): number[] {
  return rows.map((row) => {
    const val = row[column];
    if (val === null || val === undefined || val === '') return NaN;
    const num = Number(val);
    return isNaN(num) ? NaN : num;
  });
}

/**
 * Fallback: generate placeholder data when no real data is available.
 */
function generatePlaceholderData(seriesName: string, count: number): number[] {
  let seed = 0;
  for (let i = 0; i < seriesName.length; i++) {
    seed += seriesName.charCodeAt(i);
  }
  const data: number[] = [];
  let val = 30 + (seed % 40);
  for (let i = 0; i < count; i++) {
    val += Math.sin(seed + i * 0.7) * 8 + Math.cos(seed * 0.3 + i) * 5;
    val = Math.max(5, Math.min(95, val));
    data.push(val);
  }
  return data;
}

/**
 * Clean up category/group labels (remove newlines, trim).
 */
function cleanLabel(s: unknown): string {
  return String(s ?? '').replace(/[\r\n]+/g, ' ').trim();
}

/**
 * Render categorical grouped bar chart.
 * X-axis = categories (e.g., Energy, Food)
 * Sub-bars within each category = groups (e.g., 12-month, 6-month)
 */
const CategoricalBarChart: React.FC<{
  series: SeriesConfig[];
  chartArea: { x: number; y: number; width: number; height: number };
  yMin: number;
  yMax: number;
  datasetRows: Record<string, unknown>[];
  categoryColumn: string;
  groupColumn: string;
  labelFontSize: number;
}> = ({ series, chartArea, yMin, yMax, datasetRows, categoryColumn, groupColumn, labelFontSize }) => {
  const { x, y, width, height } = chartArea;
  const yRange = yMax - yMin || 1;

  // Extract unique categories and groups preserving order
  const seen = new Set<string>();
  const categories: string[] = [];
  for (const row of datasetRows) {
    const cat = cleanLabel(row[categoryColumn]);
    if (!seen.has(cat)) {
      seen.add(cat);
      categories.push(cat);
    }
  }

  const seenGroups = new Set<string>();
  const groups: string[] = [];
  for (const row of datasetRows) {
    const grp = cleanLabel(row[groupColumn]);
    if (!seenGroups.has(grp)) {
      seenGroups.add(grp);
      groups.push(grp);
    }
  }

  // Build a lookup: category -> group -> value
  const valueMap = new Map<string, Map<string, number>>();
  // Also find the value column (first numeric column that's not in series names)
  let valueColumn: string | null = null;
  if (datasetRows.length > 0) {
    for (const key of Object.keys(datasetRows[0])) {
      if (key !== categoryColumn && key !== groupColumn) {
        const val = datasetRows[0][key];
        if (typeof val === 'number' || (typeof val === 'string' && !isNaN(Number(val)) && val !== '')) {
          valueColumn = key;
          break;
        }
      }
    }
  }

  if (valueColumn) {
    for (const row of datasetRows) {
      const cat = cleanLabel(row[categoryColumn]);
      const grp = cleanLabel(row[groupColumn]);
      const val = Number(row[valueColumn]);
      if (!isNaN(val)) {
        if (!valueMap.has(cat)) valueMap.set(cat, new Map());
        valueMap.get(cat)!.set(grp, val);
      }
    }
  }

  // Build color map from series config
  const colorMap = new Map<string, string>();
  for (const s of series) {
    colorMap.set(s.name, s.color);
  }

  const numCategories = categories.length;
  const numGroups = groups.length;
  if (numCategories === 0 || numGroups === 0) return null;

  // Layout: divide width into category slots, with gaps between categories
  const categoryGap = width * 0.15 / numCategories; // gap between category groups
  const categorySlotWidth = (width - categoryGap * (numCategories - 1)) / numCategories;
  const barWidth = (categorySlotWidth * 0.8) / numGroups;
  const barGroupOffset = categorySlotWidth * 0.1; // padding within category

  // Baseline y position (where value = 0)
  const baselineY = y + height - ((0 - yMin) / yRange) * height;

  return (
    <Group>
      {categories.map((cat, catIdx) => {
        const catX = x + catIdx * (categorySlotWidth + categoryGap);
        const catValues = valueMap.get(cat);

        return (
          <Group key={cat}>
            {groups.map((grp, grpIdx) => {
              const val = catValues?.get(grp) ?? 0;
              const color = colorMap.get(grp) ?? '#999';
              const barX = catX + barGroupOffset + grpIdx * barWidth;

              // Bar extends from baseline to value
              const valY = y + height - ((val - yMin) / yRange) * height;
              const barTop = Math.min(valY, baselineY);
              const barH = Math.abs(valY - baselineY);

              return (
                <React.Fragment key={`${cat}-${grp}`}>
                  <Rect
                    x={barX}
                    y={barTop}
                    width={barWidth * 0.9}
                    height={Math.max(barH, 1)}
                    fill={color}
                    opacity={0.85}
                  />
                  {/* Value label on top of bar */}
                  <Text
                    x={barX}
                    y={val >= 0 ? barTop - 14 : barTop + barH + 2}
                    text={val.toFixed(1) + '%'}
                    fontSize={labelFontSize}
                    fontFamily="Arial"
                    fill="#333"
                    width={barWidth * 0.9}
                    align="center"
                  />
                </React.Fragment>
              );
            })}
            {/* Category label below the group */}
            <Text
              x={catX}
              y={y + height + 8}
              text={cat}
              fontSize={labelFontSize}
              fontFamily="Arial"
              fill="#333"
              width={categorySlotWidth}
              align="center"
            />
          </Group>
        );
      })}
    </Group>
  );
};

const DataSeriesElement: React.FC<DataSeriesElementProps> = ({
  series,
  chartArea,
  yMin,
  yMax,
  datasetRows,
  barGrouping,
  categoryColumn,
  groupColumn,
  barLabelFontSize,
  barStacking,
  onContextMenu,
}) => {
  const { x, y, width, height } = chartArea;
  const yRange = yMax - yMin || 1;

  // Categorical grouped bar chart mode
  if (
    barGrouping === 'by_category' &&
    categoryColumn &&
    groupColumn &&
    datasetRows &&
    datasetRows.length > 0
  ) {
    return (
      <CategoricalBarChart
        series={series}
        chartArea={chartArea}
        yMin={yMin}
        yMax={yMax}
        datasetRows={datasetRows}
        categoryColumn={categoryColumn}
        groupColumn={groupColumn}
        labelFontSize={barLabelFontSize ?? 10}
      />
    );
  }

  // Stacked bar rendering
  if (barStacking === 'stacked' && datasetRows && datasetRows.length > 0) {
    const visibleBarSeries = series.filter((s) => s.visible && s.chart_type === 'bar');
    if (visibleBarSeries.length > 0) {
      const dataCount = datasetRows.length;
      const barPadding = width * 0.02;
      const usableWidth = width - barPadding * 2;
      const barWidth = (usableWidth / Math.max(dataCount, 1)) * 0.7;

      // Pre-compute stack totals for each data point (for line overlay)
      const stackTotals: number[] = [];
      for (let di = 0; di < dataCount; di++) {
        let total = 0;
        for (const s of visibleBarSeries) {
          const val = Number(datasetRows[di]?.[s.column]);
          if (!isNaN(val)) total += val;
        }
        stackTotals.push(total);
      }

      return (
        <Group>
          {Array.from({ length: dataCount }, (_, di) => {
            let stackY = y + height;
            return (
              <Group key={`stack-${di}`}>
                {visibleBarSeries.map((s) => {
                  const val = Number(datasetRows[di]?.[s.column]);
                  if (isNaN(val) || val === 0) return null;
                  const barH = (Math.abs(val) / (yMax - yMin || 1)) * height;
                  stackY -= barH;
                  const bx = x + barPadding + (di / Math.max(dataCount - 1, 1)) * usableWidth - barWidth / 2;
                  return (
                    <Rect
                      key={`${s.name}-${di}`}
                      x={bx}
                      y={stackY}
                      width={barWidth}
                      height={Math.max(barH, 0.5)}
                      fill={s.color}
                      opacity={0.85}
                    />
                  );
                })}
              </Group>
            );
          })}
          {/* Render non-bar series (lines) at the stack total position */}
          {series.filter((s) => s.visible && s.chart_type !== 'bar').map((s) => {
            const points: number[] = [];
            for (let di = 0; di < dataCount; di++) {
              const px = x + barPadding + (di / Math.max(dataCount - 1, 1)) * usableWidth;
              // Use stack total as the y value so line sits on top of stacked bars
              const totalVal = stackTotals[di];
              const py = y + height - ((totalVal - yMin) / (yMax - yMin || 1)) * height;
              points.push(px, py);
            }
            return (
              <Line
                key={s.name}
                points={points}
                stroke={s.color}
                strokeWidth={s.line_width}
                lineCap="round"
                lineJoin="round"
              />
            );
          })}
        </Group>
      );
    }
  }

  // Helper: trigger context menu for a series on right-click
  const handleSeriesContextMenu = (seriesName: string, e: any) => {
    if (!onContextMenu) return;
    e.evt.preventDefault();
    const stage = e.target.getStage();
    const pointerPos = stage?.getPointerPosition();
    if (pointerPos) {
      onContextMenu(`series_${seriesName}`, pointerPos.x, pointerPos.y);
    }
  };

  // Standard rendering (by_series / default)
  const visibleSeries = series.filter((s) => s.visible);
  const barSeriesCount = visibleSeries.filter((s) => s.chart_type === 'bar').length;

  let barGroupIndex = 0;

  return (
    <Group>
      {visibleSeries.map((s) => {
        // Use real data if available, otherwise placeholder
        const data =
          datasetRows && datasetRows.length > 0
            ? extractSeriesData(datasetRows, s.column)
            : generatePlaceholderData(s.name, 12);

        const dataCount = data.length;
        // Filter out NaN for valid rendering
        const validData = data.map((v, i) => ({ value: v, index: i })).filter((d) => !isNaN(d.value));

        if (s.chart_type === 'bar') {
          const currentBarIndex = barGroupIndex++;
          const barPadding = width * 0.02;
          const usableWidth = width - barPadding * 2;
          const totalBarWidth = usableWidth / Math.max(dataCount, 1);
          const singleBarWidth = (totalBarWidth * 0.7) / Math.max(barSeriesCount, 1);
          const barOffset =
            currentBarIndex * singleBarWidth -
            (barSeriesCount * singleBarWidth) / 2 +
            singleBarWidth / 2;

          return (
            <Group key={s.name}>
              {validData.map((d) => {
                const bx =
                  x + barPadding +
                  (d.index / Math.max(dataCount - 1, 1)) * usableWidth +
                  barOffset -
                  singleBarWidth / 2;
                const barHeight = ((d.value - yMin) / yRange) * height;
                const by = y + height - barHeight;
                return (
                  <Rect
                    key={d.index}
                    x={bx}
                    y={by}
                    width={singleBarWidth}
                    height={Math.max(barHeight, 0)}
                    fill={s.color}
                    opacity={0.8}
                    onContextMenu={(e) => handleSeriesContextMenu(s.name, e)}
                  />
                );
              })}
            </Group>
          );
        }

        // Line or area chart
        const points: number[] = [];
        validData.forEach((d) => {
          const px = x + (d.index / Math.max(dataCount - 1, 1)) * width;
          const py = y + height - ((d.value - yMin) / yRange) * height;
          points.push(px, py);
        });

        if (s.chart_type === 'area' && validData.length > 0) {
          // Area chart: closed polygon filled to baseline
          const areaPoints = [...points];
          const lastX = x + (validData[validData.length - 1].index / Math.max(dataCount - 1, 1)) * width;
          const firstX = x + (validData[0].index / Math.max(dataCount - 1, 1)) * width;
          areaPoints.push(lastX, y + height);
          areaPoints.push(firstX, y + height);
          return (
            <React.Fragment key={s.name}>
              <Line
                points={areaPoints}
                fill={s.color}
                opacity={0.3}
                closed
                onContextMenu={(e) => handleSeriesContextMenu(s.name, e)}
              />
              <Line
                points={points}
                stroke={s.color}
                strokeWidth={s.line_width}
                lineCap="round"
                lineJoin="round"
                hitStrokeWidth={20}
                onContextMenu={(e) => handleSeriesContextMenu(s.name, e)}
              />
            </React.Fragment>
          );
        }

        return (
          <React.Fragment key={s.name}>
            {/* Invisible wider hit area for easier right-click targeting on thin lines */}
            <Line
              points={points}
              stroke="transparent"
              strokeWidth={20}
              lineCap="round"
              lineJoin="round"
              onContextMenu={(e) => handleSeriesContextMenu(s.name, e)}
            />
            <Line
              points={points}
              stroke={s.color}
              strokeWidth={s.line_width}
              lineCap="round"
              lineJoin="round"
              hitStrokeWidth={20}
              onContextMenu={(e) => handleSeriesContextMenu(s.name, e)}
            />
          </React.Fragment>
        );
      })}
    </Group>
  );
};

export default DataSeriesElement;
