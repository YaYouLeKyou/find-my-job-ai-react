import React, { useEffect, useState } from 'react';

const AdComponent = ({ format = 'auto', style = {} }) => {
  const [adLoaded, setAdLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    // Wait for AdSense to load
    const checkAdSense = setInterval(() => {
      if (window.adsbygoogle) {
        clearInterval(checkAdSense);
        try {
          (window.adsbygoogle = window.adsbygoogle || []).push({});
          setAdLoaded(true);
        } catch (err) {
          console.error('AdSense error:', err);
          setHasError(true);
        }
      }
    }, 500);

    // Timeout after 5 seconds
    const timer = setTimeout(() => {
      clearInterval(checkAdSense);
      if (!adLoaded) {
        setHasError(true);
      }
    }, 5000);

    return () => {
      clearInterval(checkAdSense);
      clearTimeout(timer);
    };
  }, [adLoaded]);

  return (
    <div style={{
      width: '100%',
      maxWidth: '728px',
      margin: '20px auto',
      padding: '20px',
      background: 'linear-gradient(135deg, rgba(124,77,255,0.08), rgba(68,138,255,0.05))',
      border: '2px solid var(--primary-color)',
      borderRadius: 'var(--radius-md)',
      textAlign: 'center',
      minHeight: '120px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '12px',
      boxShadow: 'var(--shadow-md)',
      ...style
    }}>
      {!adLoaded && !hasError && (
        <div style={{
          color: 'var(--primary-color)',
          fontSize: '0.9rem',
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
          Chargement de la publicité...
        </div>
      )}
      {hasError && (
        <div style={{
          background: 'rgba(124, 77, 255, 0.1)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(124, 77, 255, 0.2)'
        }}>
          <div style={{ color: 'var(--primary-color)', fontSize: '0.85rem', fontWeight: '600', marginBottom: '4px' }}>
            📢 Espace publicitaire
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
            Les publicités apparaîtront après approbation AdSense
          </div>
        </div>
      )}
      <ins
        className="adsbygoogle"
        style={{ 
          display: 'block', 
          textAlign: 'center',
          minHeight: '100px',
          width: '100%'
        }}
        data-ad-client="ca-pub-5351020915477002"
        data-ad-slot="1234567890"
        data-ad-format={format}
        data-full-width-responsive="true"
      ></ins>
    </div>
  );
};

export default AdComponent;
