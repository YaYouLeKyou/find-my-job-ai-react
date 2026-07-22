import { Helmet } from 'react-helmet-async';

const JobSchema = ({ job }) => {
  if (!job) return null;

  const schema = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": job.title || "",
    "description": job.description || job.title || "",
    "datePosted": job.date || new Date().toISOString(),
    "employmentType": job.contract || "FULL_TIME",
    "hiringOrganization": {
      "@type": "Organization",
      "name": job.company || "Company",
      "sameAs": job.company_url || "https://find-my-job-ai.netlify.app"
    },
    "jobLocation": {
      "@type": "Place",
      "address": {
        "@type": "PostalAddress",
        "addressLocality": job.location || "France",
        "addressCountry": "FR"
      }
    },
    "url": job.link || "https://find-my-job-ai.netlify.app"
  };

  // Add salary if available
  if (job.salary || job.tjm) {
    schema.baseSalary = {
      "@type": "MonetaryAmount",
      "currency": "EUR",
      "value": {
        "@type": "QuantitativeValue",
        "value": job.salary || job.tjm,
        "unitText": "YEAR"
      }
    };
  }

  // Add valid through date (30 days from posting by default)
  if (job.date) {
    const postedDate = new Date(job.date);
    const validThrough = new Date(postedDate);
    validThrough.setDate(validThrough.getDate() + 30);
    schema.validThrough = validThrough.toISOString();
  }

  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(schema, null, 2)}
      </script>
    </Helmet>
  );
};

export default JobSchema;