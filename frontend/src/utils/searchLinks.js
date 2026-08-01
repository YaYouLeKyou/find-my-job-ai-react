/**
 * Utility function to generate direct search links for job platforms
 * Used by App.jsx for external search links
 */

export function generateSearchLinks(jobTitle, langCode, agentType) {
    const q = encodeURIComponent(jobTitle);
    const qSlug = q.replace(/%20/g, '-');

    const categories = {
        fr: {
            'Généralistes France': [
                ['Indeed France', `https://fr.indeed.com/jobs?q=${q}`],
                ['HelloWork', `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=${q}`],
                ['Glassdoor FR', `https://www.glassdoor.fr/emploi/emploi.htm?sc.keyword=${q}`],
                ['France Travail', `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}`],
                ['APEC', `https://www.apec.fr/offres-d-emploi-cadre/recherche.html?motsCles=${q}`],
                ['Monster FR', `https://www.monster.fr/emploi/recherche?q=${q}`],
            ],
            'Tech & Cadres': [
                ['Welcome to the Jungle', `https://www.welcometothejungle.com/fr/jobs?query=${q}`],
                ['JobTeaser', `https://www.jobteaser.com/fr/jobs?query=${q}`],
                ['LinkedIn FR', `https://fr.linkedin.com/jobs/search/?keywords=${q}`],
            ],
        },
        en: {
            'Remote & Global': [
                ['Remote OK', `https://remoteok.com/remote-${qSlug}-jobs`],
                ['Indeed Global', `https://www.indeed.com/jobs?q=${q}`],
                ['Glassdoor Global', `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`],
                ['LinkedIn Global', `https://www.linkedin.com/jobs/search/?keywords=${q}`],
            ],
            'Tech & Professionals': [
                ['Reed.co.uk', `https://www.reed.co.uk/jobs/${qSlug}-jobs`],
                ['Dice (Tech US)', `https://www.dice.com/jobs?q=${q}`],
                ['LinkedIn US', `https://www.linkedin.com/jobs/search/?keywords=${q}`],
            ],
        },
    };

    const globalLinks = {
        'Remote OK': `https://remoteok.com/remote-${qSlug}-jobs`,
        'Indeed Global': `https://www.indeed.com/jobs?q=${q}`,
        'LinkedIn Global': `https://www.linkedin.com/jobs/search/?keywords=${q}`,
        'Glassdoor Global': `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}`,
        'France Travail (API)': `https://candidat.pole-emploi.fr/offres/recherche?motsCles=${q}&offresPartenaires=true`,
        'Adzuna (API)': `https://www.adzuna.fr/emploi?q=${q}`,
    };

    const freelanceLinks = {
        'Malt': `https://www.malt.fr/search?query=${q}`,
        'Upwork': `https://www.upwork.com/nx/search/jobs/?q=${q}`,
        'Freelancer': `https://www.freelancer.com/jobs/?keyword=${q}`,
        'Toptal': `https://www.toptal.com/talent/apply`,
        'Codeur.com': `https://www.codeur.com/missions?keyword=${q}`,
        'Fiverr': `https://www.fiverr.com/search/gigs?query=${q}`,
    };

    const recruiterLinks = {
        'LinkedIn Recruiter': `https://www.linkedin.com/talent/search?keywords=${q}`,
        'Indeed CV': `https://www.indeed.com/hire/resumes?q=${q}`,
        'APEC Candidats': `https://www.apec.fr/candidat/recherche-candidats.html?motsCles=${q}`,
        'Monster CV': `https://www.monster.fr/employeurs/recherche-cv?keyword=${q}`,
    };

    const langCategories = categories[langCode] || {};
    const allLinks = [];

    Object.entries(langCategories).forEach(([category, links]) => {
        allLinks.push({ category, links });
    });
    allLinks.push({ category: 'Global', links: Object.entries(globalLinks) });

    if (agentType === 'freelance') {
        allLinks.push({ category: '🚀 Freelance', links: Object.entries(freelanceLinks) });
    } else if (agentType === 'recruiter') {
        allLinks.push({ category: '👷 Recruitment', links: Object.entries(recruiterLinks) });
    }

    return allLinks;
}