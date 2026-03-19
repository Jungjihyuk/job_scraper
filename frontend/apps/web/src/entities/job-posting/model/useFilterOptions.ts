import { useEffect, useState } from 'react'
import { fetchJobCategories, fetchExperiences, fetchLocations, fetchDomains, fetchTechnologies } from '../api/jobPostingApi'

type UseFilterOptionsResult = {
  categories: string[]
  experiences: string[]
  locations: string[]
  domains: string[]
  technologies: string[]
  loading: boolean
}

export function useFilterOptions(): UseFilterOptionsResult {
  const [categories, setCategories] = useState<string[]>([])
  const [experiences, setExperiences] = useState<string[]>([])
  const [locations, setLocations] = useState<string[]>([])
  const [domains, setDomains] = useState<string[]>([])
  const [technologies, setTechnologies] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [catData, expData, locData, domData, techData] = await Promise.all([
          fetchJobCategories(),
          fetchExperiences(),
          fetchLocations(),
          fetchDomains(),
          fetchTechnologies(),
        ])
        setCategories(catData.categories)
        setExperiences(expData.experiences)
        setLocations(locData.locations)
        setDomains(domData.domains)
        setTechnologies(techData.technologies)
      } catch {
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return { categories, experiences, locations, domains, technologies, loading }
}
