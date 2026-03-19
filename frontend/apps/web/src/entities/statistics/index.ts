export {
  useSpecialtyByLocation,
  useExperienceBySpecialty,
  usePostingTrends,
  useDomainDistribution,
  useTechnologyTrends,
} from './model/useStatistics'
export {
  fetchSpecialtyByLocation,
  fetchExperienceBySpecialty,
  fetchPostingTrends,
  fetchAvailableYears,
  fetchDomainDistribution,
  fetchTechnologyTrends,
  fetchAvailableTechnologies,
} from './api/statisticsApi'
export {
  transformStackedBar,
  transformHorizontalBar,
  transformLineChart,
} from './lib/transforms'
export type { RechartsDatum, StackedBarData, LineChartDatum, LineChartData } from './model/types'
