import React from 'react';

export default function HeaderButtons({ onToggleDarkMode }) {
  return (
    <div className="header-buttons-container">
      {/* Feedback Button - Top Right */}
      <a
        href="mailto:findmyworkai@gmail.com"
        className="feedback-button"
        style={{
          position: 'fixed',
          top: '20px',
          right: '120px',
          zIndex: '1000',
          background: 'var(--primary-gradient)',
          color: 'white',
          padding: '12px 20px',
          borderRadius: 'var(--radius-full)',
          textDecoration: 'none',
          fontWeight: '700',
          fontSize: '0.9rem',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'var(--font-sans)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = 'var(--shadow-xl)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
        }}
      >
        💬 Feedback
      </a>

      {/* Dark Mode Button - Top Right, next to Feedback */}
      <button
        onClick={onToggleDarkMode}
        className="dark-mode-button"
        style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: '1000',
          background: 'var(--surface-color)',
          color: 'var(--text-primary)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-full)',
          border: '1px solid var(--border-color)',
          fontWeight: '600',
          fontSize: '0.9rem',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'transform var(--transition-fast), box-shadow var(--transition-fast), background var(--transition-fast)',
          cursor: 'pointer',
          fontFamily: 'var(--font-sans)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = 'var(--shadow-xl)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
        }}
      >
        🌓 Mode
      </button>
    </div>
  );
}