import { Helmet } from 'react-helmet-async';

const SEO = ({
  title = 'Job Bridge - Find Your Next Career Move',
  description = 'Connect with top employers and discover opportunities matched to your skills.',
  keywords = 'jobs, career, employment, job search, AI, FindMyJobAI, job matching, CV analysis',
  image = 'https://findmyjobai.com/og-image.png',
  url = 'https://find-my-job-ai.netlify.app',
  type = 'website'
}) => {
  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{title}</title>
      <meta name="title" content={title} />
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      <meta name="author" content="Yanès Hadiouche" />
      <meta name="robots" content="index, follow" />

      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={url} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />

      {/* Twitter */}
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={url} />
      <meta property="twitter:title" content={title} />
      <meta property="twitter:description" content={description} />
      <meta property="twitter:image" content={image} />

      {/* Canonical URL */}
      <link rel="canonical" href={url} />
    </Helmet>
  );
};

export default SEO;