import { useMemo } from 'react';

/**
 * Custom hook to filter jobs based on various criteria
 * @param {Array} jobs - Array of job objects to filter
 * @param {Object} filters - Filter criteria object
 * @returns {Array} - Filtered array of jobs
 */
export const useFilteredJobs = (jobs, filters) => {
  return useMemo(() => {
    if (!jobs || !Array.isArray(jobs)) return [];

    return jobs.filter(job => {
      // Match score filter
      if (filters.minMatchScore > 0 && job.match_score < filters.minMatchScore) {
        return false;
      }

      // Company type filter
      if (filters.companyTypes.length > 0 &&
        !filters.companyTypes.includes(job.company_type)) {
        return false;
      }

      // Work mode filter
      if (filters.workModes.length > 0 &&
        !filters.workModes.includes(job.work_mode)) {
        return false;
      }

      // Salary filter with AI estimation option
      if (filters.minSalary > 0) {
        const jobMinSalary = job.normalized_salary?.min || 0;
        const aiEstimatedSalary = job.ai_estimated_salary?.min || 0;
        const effectiveSalary = filters.includeAISalary ? Math.max(jobMinSalary, aiEstimatedSalary) : jobMinSalary;

        if (effectiveSalary < filters.minSalary) {
          return false;
        }
      }

      // Offer freshness filter
      if (filters.offerFreshness && filters.offerFreshness !== 'all') {
        const postedDate = job.posted_date ? new Date(job.posted_date) : new Date();
        const now = new Date();
        const hoursDiff = (now - postedDate) / (1000 * 60 * 60);

        if (filters.offerFreshness === '24h' && hoursDiff > 24) return false;
        if (filters.offerFreshness === '3d' && hoursDiff > 72) return false;
        if (filters.offerFreshness === '7d' && hoursDiff > 168) return false;
      }

      // Agent-specific filters
      if (filters.contractTypes && filters.contractTypes.length > 0 &&
        !filters.contractTypes.includes(job.contract_type)) {
        return false;
      }

      if (filters.employerTypes && filters.employerTypes.length > 0) {
        const employerType = job.employer_type || job.company_type;
        if (!filters.employerTypes.includes(employerType)) {
          return false;
        }
      }

      if (filters.remoteRhythm && job.remote_rhythm !== filters.remoteRhythm) {
        return false;
      }

      if (filters.benefits && filters.benefits.length > 0) {
        const jobBenefits = job.benefits || [];
        const hasRequiredBenefit = filters.benefits.some(benefit =>
          jobBenefits.includes(benefit)
        );
        if (!hasRequiredBenefit) {
          return false;
        }
      }

      if (filters.companySize && job.company_size !== filters.companySize) {
        return false;
      }

      if (filters.intermediary && job.intermediary !== filters.intermediary) {
        return false;
      }

      if (filters.missionDuration && job.mission_duration !== filters.missionDuration) {
        return false;
      }

      if (filters.minTJM > 0 && (job.tjm || 0) < filters.minTJM) {
        return false;
      }

      if (filters.startNotice && job.start_notice !== filters.startNotice) {
        return false;
      }

      if (filters.candidateAvailability && job.availability !== filters.candidateAvailability) {
        return false;
      }

      if (filters.candidateType && job.candidate_type !== filters.candidateType) {
        return false;
      }

      if (filters.maxSalaryExpectation > 0 && (job.salary_expectation || 0) > filters.maxSalaryExpectation) {
        return false;
      }

      if (filters.seniorityLevel && job.seniority !== filters.seniorityLevel) {
        return false;
      }

      if (filters.softSkills && filters.softSkills.length > 0) {
        const jobSoftSkills = job.soft_skills || [];
        const hasRequiredSkill = filters.softSkills.some(skill =>
          jobSoftSkills.includes(skill)
        );
        if (!hasRequiredSkill) {
          return false;
        }
      }

      // Tech stack filters (Must Have)
      if (filters.techStackMustHave && filters.techStackMustHave.length > 0) {
        const jobTechStack = job.tech_stack || [];
        const hasAllRequiredTech = filters.techStackMustHave.every(tech =>
          jobTechStack.includes(tech)
        );
        if (!hasAllRequiredTech) {
          return false;
        }
      }

      // Tech stack filters (Exclude)
      if (filters.techStackExclude && filters.techStackExclude.length > 0) {
        const jobTechStack = job.tech_stack || [];
        const hasExcludedTech = filters.techStackExclude.some(tech =>
          jobTechStack.includes(tech)
        );
        if (hasExcludedTech) {
          return false;
        }
      }

      return true;
    });
  }, [jobs, filters]);
};

export default useFilteredJobs;
