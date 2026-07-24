import React from 'react';

const JobSkeleton = () => (
  <div className="job-card" style={{ opacity: 0.7 }}>
    <div className="job-card-header">
      <div className="job-info" style={{ width: '100%' }}>
        <div style={{ height: '24px', background: 'var(--border-light)', borderRadius: '4px', width: '70%', marginBottom: '12px' }} className="skeleton-pulse"></div>
        <div style={{ height: '18px', background: 'var(--border-light)', borderRadius: '4px', width: '40%' }} className="skeleton-pulse"></div>
      </div>
      <div style={{ width: '60px', height: '24px', background: 'var(--border-light)', borderRadius: '12px' }} className="skeleton-pulse"></div>
    </div>
    <div className="job-card-meta">
      {[1, 2, 3].map(i => (
        <div key={i} style={{ width: '80px', height: '24px', background: 'var(--border-light)', borderRadius: '4px' }} className="skeleton-pulse"></div>
      ))}
    </div>
    <div className="job-card-actions" style={{ borderTop: 'none' }}>
      <div style={{ flex: 1, height: '40px', background: 'var(--border-light)', borderRadius: '8px' }} className="skeleton-pulse"></div>
      <div style={{ flex: 1, height: '40px', background: 'var(--border-light)', borderRadius: '8px' }} className="skeleton-pulse"></div>
    </div>
  </div>
);

export default JobSkeleton;
