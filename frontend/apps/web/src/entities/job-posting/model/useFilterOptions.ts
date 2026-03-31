import { useEffect, useState } from 'react'
import { fetchJobCategories, fetchExperiences, fetchLocations, fetchDomains, fetchTechnologies, fetchCompanyTypes } from '../api/jobPostingApi'

type UseFilterOptionsResult = {
  categories: string[]
  experiences: string[]
  locations: string[]
  domains: string[]
  technologies: string[]
  companyTypes: string[]
  loading: boolean
}

export function useFilterOptions(): UseFilterOptionsResult {
  const [categories, setCategories] = useState<string[]>([])
  const [experiences, setExperiences] = useState<string[]>([])
  const [locations, setLocations] = useState<string[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [technologies, setTechnologies] = useState<string[]>([])
  const [companyTypes, setCompanyTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [catData, expData, locData, domData, techData, ctData] = await Promise.all([
          fetchJobCategories(),
          fetchExperiences(),
          fetchLocations(),
          fetchDomains(),
          fetchTechnologies(),
          fetchCompanyTypes(),
        ])
        setCategories(catData.categories)
        setExperiences(expData.experiences)
        setLocations(locData.locations)
        setDomains(domData.domains)
        setTechnologies(techData.technologies)
        setCompanyTypes(ctData.company_types)
      } catch {
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return { categories, experiences, locations, domains, technologies, companyTypes, loading }
}
