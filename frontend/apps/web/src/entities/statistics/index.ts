export {
  useSpecialtyByLocation,
  useExperienceBySpecialty,
  usePostingTrends,
  useDomainDistribution,
  useCompanyTypeDistribution,
  useDomainByCompanyType,
  useTechnologyByCompanyType,
  useTechnologyTrends,
} from './model/useStatistics'
export {
  fetchSpecialtyByLocation,
  fetchExperienceBySpecialty,
  fetchPostingTrends,
  fetchAvailableYears,
  fetchDomainDistribution,
  fetchCompanyTypeDistribution,
  fetchDomainByCompanyType,
  fetchTechnologyByCompanyType,
  fetchTechnologyTrends,
  fetchAvailableTechnologies,
} from './api/statisticsApi'
export {
  transformStackedBar,
  transformHorizontalBar,
  transformLineChart,
  transformTreemap,
  transformRadar,
} from './lib/transforms'
export type { RechartsDatum, StackedBarData, LineChartDatum, LineChartData, TreemapNode, RadarDatum } from './model/types'
