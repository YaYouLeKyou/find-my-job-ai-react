import React, { useEffect, useState } from 'react';

const APPS = [
  {
    id: 'job',
    emoji: '🔍',
    title: 'FindMyJobAI',
    subtitle: 'Recherche d\'emploi CDI / CDD',
    description: 'Analysez votre CV, recevez des recommandations de carrière IA, et trouvez les meilleures offres sur 10+ plateformes en un clic.',
    features: ['Analyse CV intelligente', 'Lettre de motivation IA', 'Multi-sources simultanés', 'Score de compatibilité'],
    sources: ['LinkedIn', 'Indeed', 'France Travail', 'Glassdoor', 'Monster'],
    gradient: 'linear-gradient(135deg, #7c4dff 0%, #448aff 100%)',
    glowColor: 'rgba(124, 77, 255, 0.25)',
    accentColor: '#7c4dff',
    tagBg: 'rgba(124, 77, 255, 0.12)',
    tagColor: '#7c4dff',
    badgeBg: 'rgba(124, 77, 255, 0.08)',
    badgeBorder: 'rgba(124, 77, 255, 0.2)',
  },
  {
    id: 'freelance',
    emoji: '🚀',
    title: 'FindMyFreelanceMissionAI',
    subtitle: 'Recherche de missions freelance',
    description: 'Trouvez des missions freelance adaptées à vos compétences, calculez votre TJM optimal et générez des propositions commerciales percutantes.',
    features: ['Calcul TJM IA', 'Proposition commerciale', 'Gestion de portefeuille', 'Missions remote/hybride'],
    sources: ['Malt', 'Upwork', 'Freelancer', 'Toptal', 'Codeur.com'],
    gradient: 'linear-gradient(135deg, #00bcd4 0%, #00897b 100%)',
    glowColor: 'rgba(0, 188, 212, 0.25)',
    accentColor: '#00bcd4',
    tagBg: 'rgba(0, 188, 212, 0.12)',
    tagColor: '#00897b',
    badgeBg: 'rgba(0, 188, 212, 0.08)',
    badgeBorder: 'rgba(0, 188, 212, 0.2)',
  },
];

export default function LandingHub({ onSelectApp }) {
  const [hovered, setHovered] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 80);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 24px',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}
    >
      {/* Hero Header */}
      <div style={{ textAlign: 'center', marginBottom: '64px', maxWidth: '680px', display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
        <div className="hero-title-container">
          <h1
            style={{
              fontSize: 'clamp(2rem, 5vw, 3.5rem)',
              fontWeight: '800',
              letterSpacing: '-0.02em',
              lineHeight: '1.15',
              marginBottom: '24px',
              color: 'var(--text-primary)',
              wordWrap: 'break-word',
              overflowWrap: 'break-word',
              WebkitTextStroke: '0.5px rgba(0, 0, 0, 0.15)',
              textShadow: '0 0 1px rgba(0, 0, 0, 0.1)',
              maxWidth: '100%',
            }}
          >
            Find Me ... AI
          </h1>
        </div>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(255, 255, 255, 0.15)',
            border: '2px solid rgba(124, 77, 255, 0.3)',
            borderRadius: '9999px',
            padding: '8px 20px',
            fontSize: '0.85rem',
            fontWeight: '800',
            color: '#7c4dff',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            marginBottom: '24px',
            boxShadow: '0 4px 15px rgba(124, 77, 255, 0.2)',
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#7c4dff', display: 'inline-block', animation: 'pulse-dot 1.5s ease-in-out infinite' }} />
          Plateforme IA multi-agents
        </div>

        <p
          style={{
            fontSize: 'clamp(1rem, 2vw, 1.3rem)',
            color: 'var(--text-primary)',
            lineHeight: '1.6',
            fontWeight: '500',
            opacity: 0.95,
            maxWidth: '600px',
            margin: '0 auto',
            padding: '0 20px',
          }}
        >
          Votre plateforme d'agents IA spécialisés pour booster votre carrière.
          Choisissez votre agent et laissez l'IA travailler pour vous.
        </p>
      </div>

      {/* App Cards Grid */}
      <div
        className="app-cards-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '24px',
          maxWidth: '900px',
          width: '100%',
          padding: '0 20px',
        }}
      >
        {APPS.map((app, idx) => (
          <button
            key={app.id}
            id={`hub-app-${app.id}`}
            onClick={() => onSelectApp(app.id)}
            onMouseEnter={() => setHovered(app.id)}
            onMouseLeave={() => setHovered(null)}
            style={{
              background: 'var(--surface-color)',
              border: `1px solid ${hovered === app.id ? app.accentColor : 'var(--border-color)'}`,
              borderRadius: '24px',
              padding: '36px 32px',
              cursor: 'pointer',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              transform: hovered === app.id ? 'translateY(-8px) scale(1.01)' : 'translateY(0) scale(1)',
              boxShadow: hovered === app.id
                ? `0 24px 60px ${app.glowColor}, 0 8px 24px rgba(0,0,0,0.12)`
                : '0 4px 20px rgba(0,0,0,0.08)',
              animationDelay: `${idx * 0.12}s`,
              animation: 'slideUp 0.5s ease both',
            }}
          >
            {/* Card Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '18px',
                  background: hovered === app.id ? app.gradient : app.badgeBg,
                  border: `1px solid ${app.badgeBorder}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.8rem',
                  flexShrink: 0,
                  transition: 'all 0.3s ease',
                  boxShadow: hovered === app.id ? `0 8px 24px ${app.glowColor}` : 'none',
                }}
              >
                {app.emoji}
              </div>
              <div>
                <h2
                  style={{
                    fontSize: '1.3rem',
                    fontWeight: '800',
                    color: 'var(--text-primary)',
                    marginBottom: '8px',
                    letterSpacing: '-0.02em',
                    lineHeight: '1.2',
                    wordWrap: 'break-word',
                    overflowWrap: 'break-word',
                  }}
                >
                  {app.title}
                </h2>
                <span
                  style={{
                    fontSize: '0.85rem',
                    fontWeight: '700',
                    color: app.accentColor,
                    background: app.tagBg,
                    border: `2px solid ${app.badgeBorder}`,
                    borderRadius: '9999px',
                    padding: '6px 14px',
                    display: 'inline-block',
                  }}
                >
                  {app.subtitle}
                </span>
              </div>
            </div>

            {/* Description */}
            <p
              style={{
                fontSize: '0.92rem',
                color: 'var(--text-secondary)',
                lineHeight: '1.65',
                margin: 0,
              }}
            >
              {app.description}
            </p>

            {/* Feature List */}
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', margin: 0, padding: 0 }}>
              {app.features.map((f) => (
                <li
                  key={f}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '0.87rem',
                    color: 'var(--text-secondary)',
                    fontWeight: '500',
                  }}
                >
                  <span
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      background: app.gradient,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      fontSize: '0.65rem',
                      color: 'white',
                      fontWeight: '800',
                    }}
                  >
                    ✓
                  </span>
                  {f}
                </li>
              ))}
            </ul>

            {/* Platform Sources */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {app.sources.map((s) => (
                <span
                  key={s}
                  style={{
                    background: app.badgeBg,
                    border: `1px solid ${app.badgeBorder}`,
                    color: app.accentColor,
                    borderRadius: '6px',
                    padding: '3px 10px',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                  }}
                >
                  {s}
                </span>
              ))}
              <span
                style={{
                  background: 'rgba(0,0,0,0.04)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-muted)',
                  borderRadius: '6px',
                  padding: '3px 10px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                }}
              >
                +5 autres
              </span>
            </div>

            {/* CTA */}
            <div
              style={{
                marginTop: '4px',
                padding: '14px 20px',
                borderRadius: '12px',
                background: hovered === app.id ? app.gradient : 'rgba(0,0,0,0.04)',
                border: `1px solid ${hovered === app.id ? 'transparent' : 'var(--border-color)'}`,
                color: hovered === app.id ? 'white' : 'var(--text-secondary)',
                fontWeight: '700',
                fontSize: '0.92rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.3s ease',
                boxShadow: hovered === app.id ? `0 6px 20px ${app.glowColor}` : 'none',
              }}
            >
              <span>Lancer l'agent</span>
              <span style={{ fontSize: '1.1rem', transition: 'transform 0.3s ease', transform: hovered === app.id ? 'translateX(4px)' : 'translateX(0)' }}>→</span>
            </div>
          </button>
        ))}
      </div>

      {/* Footer */}
      <div className="hub-footer">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            🤖 Propulsé par
            <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Gemini</span>
            <span style={{ opacity: 0.5 }}>·</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Groq</span>
            <span style={{ opacity: 0.5 }}>·</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Llama</span>
            <span style={{ opacity: 0.5 }}>·</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>Ollama</span>
          </span>
          <span style={{ opacity: 0.3, fontWeight: '900' }}>|</span>
          <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>by Yanès Hadiouche</span>
        </div>
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.7); }
        }
      `}</style>
    </div>
  );
}
