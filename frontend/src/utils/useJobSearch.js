import { useState, useEffect } from 'react';
import { LANGS, STRINGS } from '../utils/translations';

const API_BASE = import.meta.env.VITE_API_URL || "";

export function useJobSearch(lang, cvData) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTime, setSearchTime] = useState(null);
  const [sourceCounts, setSourceCounts] = useState({});
  const [searchHistory, setSearchHistory] = useState([]);

  const currentLangCode = LANGS[lang].code;
  const S = STRINGS[currentLangCode];

  useEffect(() => {
    const savedHistory = localStorage.getItem('searchHistory');
    if (savedHistory) setSearchHistory(JSON.parse(savedHistory));
  }, []);

  const searchJobs = async (params) => {
    const { searchQuery, location, numAds, contract, remote, globalSearch, selectedSources, rankingEngine, customGeminiKey } = params;
    
    if (!searchQuery) return;

    const startTime = Date.now();
    setLoading(true);
    setError("");
    setJobs([]);
    setSourceCounts({});

    try {
      const response = await fetch(`${API_BASE}/api/search-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: searchQuery,
          location: globalSearch ? "" : location,
          num_ads: numAds,
          contract: contract,
          remote: remote,
          global_search: globalSearch,
          selected_sources: selectedSources,
          sort_option: S.sort_relevant,
          ranking_engine: rankingEngine,
          custom_gemini_key: customGeminiKey || null,
          lang_code: currentLangCode,
          lang_label: LANGS[lang].label,
          cv_data: cvData
        })
      });

      if (!response.ok) throw new Error("Erreur de communication avec le serveur d'offres.");

      const data = await response.json();
      const results = data.results || [];
      
      setJobs(results);
      setSourceCounts(data.source_counts || {});
      
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      setSearchTime(duration);

      const newHistory = [
        { query: searchQuery, time: new Date().toISOString(), count: results.length },
        ...searchHistory.filter(h => h.query !== searchQuery)
      ].slice(0, 10);
      
      setSearchHistory(newHistory);
      localStorage.setItem('searchHistory', JSON.stringify(newHistory));
      
      return { success: true, count: results.length, duration };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = () => {
    setSearchHistory([]);
    localStorage.removeItem('searchHistory');
  };

  return {
    jobs,
    loading,
    error,
    searchTime,
    sourceCounts,
    searchHistory,
    searchJobs,
    clearHistory
  };
}
