/* eslint-disable */
const fs = require('fs');
const path = require('path');

// Configuration
const BASE_URL = 'https://findmyjobai.com';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000';

// Main pages to include in sitemap
const staticPages = [
    { url: '/', priority: 1.0, changefreq: 'daily' },
    { url: '/#jobs', priority: 0.9, changefreq: 'daily' },
    { url: '/#freelance', priority: 0.9, changefreq: 'daily' },
];

// Fetch jobs from API
async function fetchJobs() {
    try {
        const response = await fetch(`${API_URL}/api/search-jobs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: 'all',
                location: '',
                num_ads: 100, // Get maximum jobs
                contract: 'all',
                remote: false,
                global_search: true,
                selected_sources: [
                    'LinkedIn', 'Indeed', 'France Travail', 'Google Jobs', 'Adzuna',
                    'Jooble', 'Glassdoor', 'ZipRecruiter', 'Simplyhired', 'Careerbuilder', 'Monster'
                ],
                sort_option: 'Pertinence (IA)',
                ranking_engine: 'Groq / Llama 3.3',
                custom_gemini_key: null,
                lang_code: 'fr',
                lang_label: 'français',
                cv_data: null
            })
        });

        if (!response.ok) {
            console.warn('Could not fetch jobs from API, using empty job list');
            return [];
        }

        const data = await response.json();
        return data.results || [];
    } catch (error) {
        console.warn('Error fetching jobs:', error.message);
        return [];
    }
}

// Generate sitemap XML
function generateSitemap(jobs) {
    const today = new Date().toISOString().split('T')[0];

    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

    // Add static pages
    for (const page of staticPages) {
        xml += '  <url>\n';
        xml += `    <loc>${BASE_URL}${page.url}</loc>\n`;
        xml += `    <lastmod>${today}</lastmod>\n`;
        xml += `    <changefreq>${page.changefreq}</changefreq>\n`;
        xml += `    <priority>${page.priority}</priority>\n`;
        xml += '  </url>\n';
    }

    // Add job pages (using job ID as slug)
    for (const job of jobs) {
        if (!job.id || !job.title) continue;

        // Create a URL-friendly slug from job title
        const slug = job.title
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '')
            .substring(0, 50);

        const jobUrl = `/#jobs/${job.id}-${slug}`;

        xml += '  <url>\n';
        xml += `    <loc>${BASE_URL}${jobUrl}</loc>\n`;
        xml += `    <lastmod>${today}</lastmod>\n`;
        xml += '    <changefreq>weekly</changefreq>\n';
        xml += '    <priority>0.7</priority>\n';
        xml += '  </url>\n';
    }

    xml += '</urlset>';
    return xml;
}

// Main function
async function main() {
    console.log('🔄 Fetching jobs from API...');
    const jobs = await fetchJobs();
    console.log(`✅ Found ${jobs.length} jobs`);

    console.log('📝 Generating sitemap...');
    const sitemap = generateSitemap(jobs);

    // Ensure public directory exists
    const publicDir = path.join(__dirname, '..', 'public');
    if (!fs.existsSync(publicDir)) {
        fs.mkdirSync(publicDir, { recursive: true });
    }

    // Write sitemap file
    const sitemapPath = path.join(publicDir, 'sitemap.xml');
    fs.writeFileSync(sitemapPath, sitemap, 'utf8');

    console.log(`✅ Sitemap generated successfully at: ${sitemapPath}`);
    console.log(`   - ${staticPages.length} static pages`);
    console.log(`   - ${jobs.length} job pages`);
    console.log(`   - Total: ${staticPages.length + jobs.length} URLs`);
}

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { generateSitemap, fetchJobs };