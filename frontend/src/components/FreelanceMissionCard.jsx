import React, { useState } from 'react';
import { ExternalLink, FileText, ChevronDown, ChevronUp, Download, Loader2, Copy, Check, Clock, Wifi, DollarSign, BarChart3 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function FreelanceMissionCard({
  mission,
  cvData,
  rankingEngine,
  customGeminiKey,
  onSaveMission,
  isSaved
}) {
  const [expanded, setExpanded] = useState(false);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [proposalContent, setProposalContent] = useState("");
  const [proposalError, setProposalError] = useState("");
  const [copied, setCopied] = useState(false);
  const [workloadLoading, setWorkloadLoading] = useState(false);
  const [workloadData, setWorkloadData] = useState(null);
  const [workloadError, setWorkloadError] = useState("");

  const getScoreColorClass = (score) => {
    if (score > 70) return "high";
    if (score > 40) return "medium";
    return "low";
  };

  const getTjmColor = (tjm) => {
    if (!tjm) return 'var(--text-muted)';
    const num = parseInt(String(tjm).replace(/\D/g, ''));
    if (num >= 600) return '#00897b';
    if (num >= 350) return '#f57c00';
    return 'var(--text-secondary)';
  };

  const handleCopyProposal = async () => {
    if (!proposalContent) return;
    try {
      await navigator.clipboard.writeText(proposalContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleGenerateProposal = async () => {
    if (!cvData) return;
    setProposalLoading(true);
    setProposalError("");

    try {
      const response = await fetch(`${API_BASE}/api/generate-letter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cv_data: cvData,
          job_title: mission.title,
          company: mission.company || mission.client || "Client",
          job_description: `[Mission Freelance]\n${mission.desc || ""}\nTJM: ${mission.tjm || "Non spécifié"}\nDurée: ${mission.duration || "Non spécifiée"}\nRemote: ${mission.remote ? "Oui" : "Non"}`,
          ranking_engine: rankingEngine,
          custom_gemini_key: customGeminiKey || null,
          lang_label: "français",
          is_freelance: true,
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Échec de génération de la proposition.");
      }

      const data = await response.json();
      setProposalContent(data.letter);
    } catch (err) {
      console.error(err);
      setProposalError(err.message);
    } finally {
      setProposalLoading(false);
    }
  };

  const handleDownload = () => {
    if (!proposalContent) return;
    const element = document.createElement("a");
    const file = new Blob([proposalContent], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `proposition_${(mission.company || mission.client || 'client').replace(/\s+/g, '_')}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleEstimateWorkload = async () => {
    setWorkloadLoading(true);
    setWorkloadError("");
    
    try {
      const response = await fetch(`${API_BASE}/api/estimate-workload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mission_title: mission.title,
          mission_description: mission.desc || mission.description || "",
          cv_data: cvData,
          ranking_engine: rankingEngine,
          custom_gemini_key: customGeminiKey || null,
          lang_label: "français"
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Échec de l'estimation de la charge de travail.");
      }

      const data = await response.json();
      setWorkloadData(data.workload);
    } catch (err) {
      console.error(err);
      setWorkloadError(err.message);
    } finally {
      setWorkloadLoading(false);
    }
  };

  const getComplexityColor = (level) => {
    switch(level) {
      case 'low': return '#4caf50';
      case 'medium': return '#ff9800';
      case 'high': return '#f44336';
      case 'very_high': return '#9c27b0';
      default: return '#757575';
    }
  };

  const getComplexityLabel = (level) => {
    switch(level) {
      case 'low': return 'Faible';
      case 'medium': return 'Moyen';
      case 'high': return 'Élevé';
      case 'very_high': return 'Très élevé';
      default: return level;
    }
  };

  return (
    <div className="job-card freelance-card">
      <div className="job-card-header">
        <div className="job-info">
          <h3>{mission.title}</h3>
          <span className="job-company" style={{ color: 'var(--freelance-primary)' }}>
            🏢 {mission.company || mission.client || "Client confidentiel"}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
          {mission.match_score !== undefined && mission.match_score !== null && (
            <span className={`score-badge ${getScoreColorClass(mission.match_score)}`}>
              Score: {mission.match_score}%
            </span>
          )}
          {mission.tjm && (
            <span
              style={{
                background: 'rgba(0,188,212,0.1)',
                border: '1px solid rgba(0,188,212,0.25)',
                color: getTjmColor(mission.tjm),
                padding: '4px 12px',
                borderRadius: '9999px',
                fontWeight: '700',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              💰 {mission.tjm}
            </span>
          )}
        </div>
      </div>

      {/* Mission Meta Info */}
      <div className="job-card-meta" style={{ flexWrap: 'wrap' }}>
        {mission.source && (
          <span className="meta-item">
            🏷️ <strong>{mission.source}</strong>
          </span>
        )}
        {mission.location && (
          <span className="meta-item">📍 {mission.location}</span>
        )}
        {mission.duration && (
          <span className="meta-item">
            <Clock size={13} />
            {mission.duration}
          </span>
        )}
        {mission.date && (
          <span className="meta-item">📅 {mission.date}</span>
        )}
        {mission.remote && (
          <span
            className="meta-item"
            style={{
              background: 'rgba(0,188,212,0.08)',
              border: '1px solid rgba(0,188,212,0.2)',
              color: 'var(--freelance-primary)',
              borderRadius: '6px',
              padding: '2px 8px',
              fontWeight: '600',
            }}
          >
            <Wifi size={12} /> Remote
          </span>
        )}
      </div>

      {/* Description snippet */}
      {mission.desc && (
        <p
          style={{
            fontSize: '0.87rem',
            color: 'var(--text-secondary)',
            lineHeight: '1.6',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {mission.desc}
        </p>
      )}

      {/* Actions */}
      <div className="job-card-actions">
        <a
          href={mission.link && mission.link !== '#' ? mission.link : undefined}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary"
          style={{ flexGrow: 1, textDecoration: 'none', textAlign: 'center' }}
        >
          <ExternalLink size={16} />
          Voir la mission
        </a>
        {onSaveMission && (
          <button
            className="btn btn-secondary"
            onClick={() => onSaveMission(mission)}
            title={isSaved ? "Retirer des favoris" : "Sauvegarder la mission"}
            style={{ flexGrow: 0, padding: '8px 12px' }}
          >
            {isSaved ? '⭐' : '☆'}
          </button>
        )}
        <button
          className="btn btn-secondary"
          style={{ flexGrow: 0, padding: '8px 12px' }}
          onClick={handleEstimateWorkload}
          title="Estimer la charge de travail"
          disabled={workloadLoading}
        >
          {workloadLoading ? <Loader2 size={16} className="spin" style={{ animation: 'spin 1s linear infinite' }} /> : <BarChart3 size={16} />}
        </button>
        <button
          className="btn btn-freelance"
          style={{ flexGrow: 1 }}
          onClick={() => setExpanded(!expanded)}
        >
          <FileText size={16} />
          Proposition commerciale
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Proposal Generator Panel */}
      {expanded && (
        <div className="letter-expander" style={{ borderColor: 'rgba(0,188,212,0.2)', background: 'rgba(0,188,212,0.03)' }}>
          {!cvData ? (
            <div className="alert alert-danger" style={{ fontSize: '0.85rem' }}>
              Veuillez d'abord uploader votre CV pour générer une proposition commerciale.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '8px 12px', background: 'rgba(0,188,212,0.06)', borderRadius: '8px', borderLeft: '3px solid var(--freelance-primary)' }}>
                🤖 L'IA va générer une proposition commerciale personnalisée adaptée au contexte freelance, incluant votre TJM et vos compétences clés.
              </div>
              
              {/* Workload Estimation Section */}
              {workloadData && (
                <div style={{
                  padding: '16px',
                  background: 'rgba(0,188,212,0.08)',
                  border: '1px solid rgba(0,188,212,0.2)',
                  borderRadius: '12px',
                  marginTop: '8px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <BarChart3 size={18} style={{ color: 'var(--freelance-primary)' }} />
                    <span style={{ fontWeight: '700', color: 'var(--freelance-primary)' }}>Estimation de charge de travail</span>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                    <div style={{ textAlign: 'center', padding: '10px', background: 'rgba(255,255,255,0.5)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Heures estimées</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '800', color: 'var(--freelance-dark)' }}>
                        {workloadData.estimated_hours}h
                      </div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '10px', background: 'rgba(255,255,255,0.5)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Complexité</div>
                      <div style={{ 
                        fontSize: '1rem', 
                        fontWeight: '700', 
                        color: getComplexityColor(workloadData.complexity_level),
                        textTransform: 'uppercase'
                      }}>
                        {getComplexityLabel(workloadData.complexity_level)}
                      </div>
                    </div>
                  </div>
                  
                  {workloadData.complexity_description && (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', fontStyle: 'italic' }}>
                      {workloadData.complexity_description}
                    </div>
                  )}
                  
                  {workloadData.key_tasks && workloadData.key_tasks.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '6px' }}>
                        Tâches principales :
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {workloadData.key_tasks.map((task, idx) => (
                          <li key={idx}>{task}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {workloadData.recommended_duration && (
                    <div style={{ 
                      marginTop: '8px', 
                      padding: '8px 12px', 
                      background: 'rgba(0,188,212,0.1)', 
                      borderRadius: '6px',
                      fontSize: '0.85rem',
                      color: 'var(--freelance-dark)',
                      fontWeight: '600'
                    }}>
                      ⏱️ Durée recommandée : {workloadData.recommended_duration}
                    </div>
                  )}
                </div>
              )}

              {workloadError && (
                <div className="alert alert-danger" style={{ fontSize: '0.85rem' }}>
                  {workloadError}
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn btn-freelance"
                  style={{ flexGrow: 1 }}
                  disabled={proposalLoading}
                  onClick={handleGenerateProposal}
                >
                  {proposalLoading ? (
                    <>
                      <Loader2 size={16} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                      Génération en cours...
                    </>
                  ) : (
                    '✨ Générer la proposition (IA)'
                  )}
                </button>
                {proposalContent && (
                  <>
                    <button
                      className="btn btn-secondary"
                      onClick={handleCopyProposal}
                      title="Copier la proposition"
                    >
                      {copied ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={handleDownload}
                    >
                      <Download size={16} />
                    </button>
                  </>
                )}
              </div>

              {proposalError && (
                <div className="alert alert-danger" style={{ fontSize: '0.85rem' }}>
                  {proposalError}
                </div>
              )}

              {proposalContent && (
                <div className="form-group">
                  <label>Votre proposition commerciale personnalisée :</label>
                  <textarea
                    className="textarea-control"
                    style={{ height: '320px', width: '100%', resize: 'vertical', borderColor: 'rgba(0,188,212,0.3)' }}
                    value={proposalContent}
                    onChange={(e) => setProposalContent(e.target.value)}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
