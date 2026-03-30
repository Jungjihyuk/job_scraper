export type { ChartResponse, AvailableYearsResponse } from '../../../shared/api'

export type RechartsDatum = Record<string, string | number>
export type StackedBarData = RechartsDatum[]
export type LineChartDatum = { date: string; count: number }
export type LineChartData = LineChartDatum[]
export type { TreemapNode, RadarDatum } from '../lib/transforms'
