import React, { useState } from 'react';
import { LANGS, STRINGS } from '../utils/translations';
import { ExternalLink, FileText, ChevronDown, ChevronUp, Download, Loader2, Copy, Check } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function JobCard({
  lang,
  job,
  cvData,
  rankingEngine,
  customGeminiKey,
  onSaveJob,
  isSaved
}) {
  const S = STRINGS[LANGS[lang].code];
  const [expanded, setExpanded] = useState(false);
  const [letterLoading, setLetterLoading] = useState(false);
  const [letterContent, setLetterContent] = useState("");
  const [letterError, setLetterError] = useState("");
  const [copied, setCopied] = useState(false);

  const getScoreColorClass = (score) => {
    if (score > 70) return "high";
    if (score > 40) return "medium";
    return "low";
  };

  const handleCopyLetter = async () => {
    if (!letterContent) return;
    try {
      await navigator.clipboard.writeText(letterContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleGenerateLetter = async () => {
    if (!cvData) return;
    setLetterLoading(true);
    setLetterError("");
    
    try {
      const response = await fetch(`${API_BASE}/api/generate-letter`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          cv_data: cvData,
          job_title: job.title,
          company: job.company,
          job_description: job.desc || "",
          ranking_engine: rankingEngine,
          custom_gemini_key: customGeminiKey || null,
          lang_label: LANGS[lang].label
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Échec de génération de la lettre.");
      }

      const data = await response.json();
      setLetterContent(data.letter);
    } catch (err) {
      console.error(err);
      setLetterError(err.message);
    } finally {
      setLetterLoading(false);
    }
  };

  const handleDownload = () => {
    if (!letterContent) return;
    const element = document.createElement("a");
    const file = new Blob([letterContent], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `lettre_${job.company.replace(/\s+/g, '_')}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div className="job-info">
          <h3>{job.title}</h3>
          <span className="job-company">🏢 {job.company}</span>
        </div>
        {job.match_score !== undefined && job.match_score !== null && (
          <span className={`score-badge ${getScoreColorClass(job.match_score)}`}>
            Score: {job.match_score}%
          </span>
        )}
      </div>

      <div className="job-card-meta">
        {job.source && <span className="meta-item">🏷️ Source : <strong>{job.source}</strong></span>}
        {job.location && <span className="meta-item">📍 {job.location}</span>}
        {job.date && <span className="meta-item">📅 {job.date}</span>}
      </div>

      <div className="job-card-actions">
        <a 
          href={job.link && job.link !== '#' ? job.link : undefined} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="btn btn-secondary"
          style={{ flexGrow: 1, textDecoration: 'none', textAlign: 'center' }}
        >
          <ExternalLink size={16} />
          {S.see_job_btn}
        </a>
        {onSaveJob && (
          <button 
            className="btn btn-secondary"
            onClick={() => onSaveJob(job)}
            title={isSaved ? "Retirer des favoris" : "Sauvegarder l'offre"}
            style={{ flexGrow: 0, padding: '8px 12px' }}
          >
            {isSaved ? '⭐' : '☆'}
          </button>
        )}
        <button 
          className="btn btn-primary"
          style={{ flexGrow: 1 }}
          onClick={() => setExpanded(!expanded)}
        >
          <FileText size={16} />
          Lettre de Motivation
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {expanded && (
        <div className="letter-expander">
          {!cvData ? (
            <div className="alert alert-danger" style={{ fontSize: '0.85rem' }}>
              Veuillez d'abord uploader votre CV pour générer la lettre.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  className="btn btn-primary"
                  style={{ flexGrow: 1 }}
                  disabled={letterLoading}
                  onClick={handleGenerateLetter}
                >
                  {letterLoading ? (
                    <>
                      <Loader2 size={16} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                      {S.letter_generating}
                    </>
                  ) : (
                    S.generate_letter_btn
                  )}
                </button>
                {letterContent && (
                  <>
                    <button 
                      className="btn btn-secondary"
                      onClick={handleCopyLetter}
                      title="Copier la lettre"
                    >
                      {copied ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                    <button 
                      className="btn btn-secondary"
                      onClick={handleDownload}
                    >
                      <Download size={16} />
                      {S.download_letter}
                    </button>
                  </>
                )}
              </div>

              {letterError && (
                <div className="alert alert-danger" style={{ fontSize: '0.85rem' }}>
                  {letterError}
                </div>
              )}

              {letterContent && (
                <div className="form-group">
                  <label>{S.letter_area_label}</label>
                  <textarea 
                    className="textarea-control"
                    style={{ height: '300px', width: '100%', resize: 'vertical' }}
                    value={letterContent}
                    onChange={(e) => setLetterContent(e.target.value)}
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