import { useEffect, useState } from 'react'
import { fetchJobCategories, fetchExperiences, fetchLocations } from '../api/jobPostingApi'

type UseFilterOptionsResult = {
  categories: string[]
  experiences: string[]
  locations: string[]
  loading: boolean
}

export function useFilterOptions(): UseFilterOptionsResult {
  const [categories, setCategories] = useState<string[]>([])
  const [experiences, setExperiences] = useState<string[]>([])
  const [locations, setLocations] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [catData, expData, locData] = await Promise.all([
          fetchJobCategories(),
          fetchExperiences(),
          fetchLocations(),
        ])
        setCategories(catData.categories)
        setExperiences(expData.experiences)
        setLocations(locData.locations)
      } catch {
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return { categories, experiences, locations, loading }
}
