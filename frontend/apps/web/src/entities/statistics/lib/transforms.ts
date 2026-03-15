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

export function transformLineChart(data: ChartResponse): LineChartData {
  const dataset = data.datasets[0]
  if (!dataset) return []
  return data.labels.map((label, i) => ({
    date: label,
    count: dataset.data[i] ?? 0,
  }))
}
