import type { ChartResponse } from '../../../shared/api'
import type { StackedBarData, LineChartData } from '../model/types'

export function transformStackedBar(data: ChartResponse): StackedBarData {
  return data.labels.map((label, labelIndex) => {
    const datum: Record<string, string | number> = { name: label }
    data.datasets.forEach((dataset) => {
      const value = dataset.data[labelIndex]
      if (value !== undefined) {
        datum[dataset.label] = value
      }
    })
    return datum
  })
}

export function transformHorizontalBar(data: ChartResponse): StackedBarData {
  const totals = data.labels.map((_, i) =>
    data.datasets.reduce((sum, ds) => sum + (ds.data[i] ?? 0), 0),
  )

  return data.labels.map((label, labelIndex) => {
    const total = totals[labelIndex] ?? 1
    const datum: Record<string, string | number> = { name: label }
    data.datasets.forEach((dataset) => {
      const raw = dataset.data[labelIndex] ?? 0
      datum[dataset.label] = total > 0 ? Math.round((raw / total) * 1000) / 10 : 0
    })
    return datum
  })
}

export type TreemapNode = { name: string; size?: number; fill?: string; groupName?: string; children?: TreemapNode[] }

const TREEMAP_BASE_COLORS = [
  [99, 102, 241],   // indigo
  [245, 158, 11],   // amber
  [16, 185, 129],   // emerald
  [239, 68, 68],    // red
  [139, 92, 246],   // violet
  [6, 182, 212],    // cyan
  [249, 115, 22],   // orange
  [20, 184, 166],   // teal
  [236, 72, 153],   // pink
  [132, 204, 22],   // lime
]

/**
 * ChartResponse → Treemap 데이터 (색상 내장).
 * 기업유형(그룹)마다 고유 색상, 도메인(자식)은 같은 색의 밝기 변형.
 */
export function transformTreemap(data: ChartResponse): TreemapNode[] {
  return data.labels.map((label, i) => {
    const [r, g, b] = TREEMAP_BASE_COLORS[i % TREEMAP_BASE_COLORS.length]
    const children = data.datasets
      .map((ds) => ({ name: ds.label, size: ds.data[i] ?? 0 }))
      .filter((d) => d.size > 0)
      .sort((a, b) => b.size - a.size)

    const fill = `rgb(${r}, ${g}, ${b})`
    return {
      name: label,
      fill,
      children: children.map((child) => ({ ...child, fill, groupName: label })),
    }
  })
}

export type RadarDatum = Record<string, string | number>

/**
 * ChartResponse → Radar 데이터 (축 전환).
 * labels=기업유형, datasets=기술 → [{tech, 대기업IT: n, 스타트업: n, ...}]
 */
export function transformRadar(data: ChartResponse): RadarDatum[] {
  return data.datasets.map((ds) => {
    const datum: RadarDatum = { subject: ds.label }
    data.labels.forEach((label, j) => {
      datum[label] = ds.data[j] ?? 0
    })
    return datum
  })
}

export function transformLineChart(data: ChartResponse): LineChartData {
  const dataset = data.datasets[0]
  if (!dataset) return []
  return data.labels.map((label, i) => ({
    date: label,
    count: dataset.data[i] ?? 0,
  }))
}
