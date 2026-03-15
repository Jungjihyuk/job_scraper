export {
  useSpecialtyByLocation,
  useExperienceBySpecialty,
  usePostingTrends,
} from './model/useStatistics'
export {
  fetchSpecialtyByLocation,
  fetchExperienceBySpecialty,
  fetchPostingTrends,
  fetchAvailableYears,
} from './api/statisticsApi'
export {
  transformStackedBar,
  transformHorizontalBar,
  transformLineChart,
} from './lib/transforms'
export type { RechartsDatum, StackedBarData, LineChartDatum, LineChartData } from './model/types'
