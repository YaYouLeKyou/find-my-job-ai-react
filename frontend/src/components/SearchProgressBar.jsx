import React, { useState, useEffect, useRef } from 'react';

const ESTIMATED_TOTAL_TIME = 60; // seconds (based on observed ~57s for full scan)
const ESTIMATED_TIME_PER_SOURCE = 5; // seconds
const ANIMATION_INTERVAL = 150; // ms between updates for smooth animation

export default function SearchProgressBar({ isSearching, totalSources, sourcesCompleted }) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef(null);
  const animFrameRef = useRef(null);

  useEffect(() => {
    if (isSearching) {
      startTimeRef.current = Date.now();
      setProgress(0);
      setElapsed(0);
      setPhase('🔍 Lancement de la recherche...');

      const animate = () => {
        if (!startTimeRef.current) return;
        const now = Date.now();
        const elapsedSec = (now - startTimeRef.current) / 1000;
        setElapsed(elapsedSec);

        // Calculate progress based on elapsed time vs estimated
        let pct = Math.min((elapsedSec / ESTIMATED_TOTAL_TIME) * 100, 95);

        // Also consider source completion if available
        if (sourcesCompleted && totalSources > 0) {
          const sourcePct = (sourcesCompleted / totalSources) * 100;
          pct = Math.max(pct, sourcePct);
        }

        setProgress(Math.round(pct));

        // Update phase description based on progress
        if (pct < 10) setPhase('🔍 Préparation de la recherche...');
        else if (pct < 25) setPhase(`📡 Interrogation des sources (${sourcesCompleted || 0}/${totalSources})...`);
        else if (pct < 50) setPhase(`⚙️ Analyse des résultats (${sourcesCompleted || 0}/${totalSources})...`);
        else if (pct < 75) setPhase('🧠 Classement par pertinence IA...');
        else if (pct < 95) setPhase('📊 Finalisation des résultats...');
        else setPhase('✅ Presque terminé...');

        if (pct < 100 && isSearching) {
          animFrameRef.current = setTimeout(animate, ANIMATION_INTERVAL);
        }
      };

      animate();
    } else {
      // Search completed - snap to 100%
      setProgress(100);
      setPhase('✅ Terminé');
      if (animFrameRef.current) clearTimeout(animFrameRef.current);
      startTimeRef.current = null;

      // Reset after a short delay
      const resetTimer = setTimeout(() => {
        setProgress(0);
        setElapsed(0);
      }, 2000);

      return () => clearTimeout(resetTimer);
    }

    return () => {
      if (animFrameRef.current) clearTimeout(animFrameRef.current);
    };
  }, [isSearching, totalSources, sourcesCompleted]);

  if (!isSearching && progress === 0) return null;

  // Determine color based on progress
  const barColor = progress < 30 ? '#6366f1' : progress < 70 ? '#7c4dff' : '#10b981';
  const bgColor = '#1e1b4b';
  
  // Format elapsed time
  const formatTime = (sec) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  return (
    <div style={{
      width: '100%',
      maxWidth: '700px',
      margin: '0 auto 16px auto',
      padding: '16px 20px',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
      borderRadius: '16px',
      border: '1px solid rgba(99, 102, 241, 0.3)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      fontFamily: "'Segoe UI', system-ui, sans-serif",
      transition: 'all 0.3s ease',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '10px',
      }}>
        <span style={{
          color: '#e2e8f0',
          fontSize: '14px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: isSearching ? '#10b981' : '#6366f1',
            display: 'inline-block',
            animation: isSearching ? 'pulse 1.5s ease-in-out infinite' : 'none',
          }} />
          {phase}
        </span>
        <span style={{
          color: '#94a3b8',
          fontSize: '13px',
          fontWeight: 500,
          fontFamily: "'Fira Code', monospace",
        }}>
          {elapsed > 0 ? formatTime(elapsed) : ''}
        </span>
      </div>

      {/* Progress Bar */}
      <div style={{
        position: 'relative',
        height: '10px',
        background: bgColor,
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.3)',
      }}>
        <div style={{
          height: '100%',
          width: `${progress}%`,
          background: `linear-gradient(90deg, ${barColor}, ${progress < 50 ? '#818cf8' : '#34d399'})`,
          borderRadius: '10px',
          transition: 'width 0.3s ease, background 0.5s ease',
          position: 'relative',
          boxShadow: `0 0 12px ${barColor}66`,
        }}>
          {/* Animated shimmer effect */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)',
            animation: 'shimmer 2s ease-in-out infinite',
            borderRadius: '10px',
          }} />
        </div>
      </div>

      {/* Bottom: percentage only */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: '8px',
      }}>
        <span style={{
          color: '#6366f1',
          fontSize: '24px',
          fontWeight: 700,
          fontFamily: "'Fira Code', monospace",
          textShadow: '0 0 20px rgba(99,102,241,0.3)',
        }}>
          {progress}%
        </span>
      </div>

      {/* CSS Keyframes injected once */}
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}