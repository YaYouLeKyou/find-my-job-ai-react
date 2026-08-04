import React, { useState, useRef, useEffect } from 'react';
import { Upload, AlertCircle, FileText, CheckCircle2, Loader2 } from 'lucide-react';
import { LANGS, STRINGS } from '../../utils/translations';
import { useAgent } from '../../context/AgentContext';
import { useAI } from '../../context/AIContext';
import CvProfile from '../CvProfile';
import AdComponent from '../AdComponent';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function FreelanceCvAnalyzer({ lang, onAnalysisSuccess, cvData: externalCvData }) {
    const S = STRINGS[LANGS[lang].code];
    const { noAiMode } = useAgent();
    const { activeModel } = useAI();

    const [dragActive, setDragActive] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [fileName, setFileName] = useState('');
    const [cvData, setCvData] = useState(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        try {
            if (externalCvData && typeof externalCvData === 'object') {
                setCvData(externalCvData);
                setFileName(externalCvData.fileName || externalCvData.nom_complet || 'CV');
            }
        } catch (err) {
            console.error('[FreelanceCvAnalyzer] Error syncing external cvData:', err);
        }
    }, [externalCvData]);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const processFile = async (file) => {
        if (!file) return;
        if (file.type !== 'application/pdf') {
            setError(S.pdf_only);
            return;
        }

        setLoading(true);
        setError(null);
        setFileName(file.name);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('selected_model', activeModel);
        formData.append('lang_label', LANGS[lang].label);
        formData.append('force_fallback_mode', noAiMode ? 'true' : 'false');

        try {
            const response = await fetch(`${API_BASE}/api/freelance/analyze-cv`, {
                method: 'POST',
                body: formData,
            });

            const contentType = response.headers.get('content-type');
            const responseText = await response.text();

            if (!response.ok) {
                let errorMessage = `${S.http_error} ${response.status}`;
                if (contentType && contentType.includes('application/json')) {
                    try {
                        const errorData = JSON.parse(responseText);
                        errorMessage = errorData.detail || errorData.error || errorMessage;
                    } catch (e) {
                        console.error('[FreelanceCvAnalyzer] Error parsing error response:', e);
                    }
                } else if (responseText.includes('<!doctype') || responseText.includes('<html')) {
                    errorMessage = `${S.backend_not_accessible} ${API_BASE}`;
                }

                if (response.status === 400) {
                    errorMessage += "\n\nCauses possibles :\n- Le fichier n'est pas un PDF\n- Le fichier est vide\n- Le PDF ne contient pas de texte extractible\n- Le texte extrait est trop court (< 50 caractères)";
                }

                throw new Error(errorMessage);
            }

            let data;
            try {
                data = JSON.parse(responseText);
            } catch (e) {
                throw new Error(S.invalid_json);
            }

            if (data.error) {
                throw new Error(data.error);
            }

            setCvData(data);
            if (data.metier) {
                onAnalysisSuccess(data);
            }
        } catch (err) {
            console.error('[FreelanceCvAnalyzer] Analysis error:', err);
            setError(err.message || S.analysis_error);
        } finally {
            setLoading(false);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) processFile(file);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        const file = e.dataTransfer.files?.[0];
        if (file) processFile(file);
    };

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
        }
    };

    return (
        <div className="card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <span>📄</span>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {S.analyze_cv}
                </h3>
                <span style={{
                    fontSize: '0.7rem',
                    background: 'var(--color-primary-100)',
                    color: 'var(--color-primary-700)',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    fontWeight: 600,
                }}>
                    FREELANCE
                </span>
            </div>

            <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={handleClick}
                onKeyDown={handleKeyDown}
                role="button"
                tabIndex={0}
                aria-label={S.upload_cv}
                style={{
                    border: `2px dashed ${dragActive ? 'var(--color-primary-500)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '32px 16px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    background: dragActive ? 'var(--color-primary-50)' : 'var(--color-surface)',
                    transition: 'all 0.2s',
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                    aria-label={S.upload_cv}
                />

                {loading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-primary-500)' }} />
                        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                            {S.analyzing_cv}
                        </span>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                        <FileText size={32} style={{ color: 'var(--color-text-muted)' }} />
                        <span style={{ color: 'var(--color-text-primary)', fontSize: '0.85rem', fontWeight: 500 }}>
                            {fileName || S.upload_cv}
                        </span>
                        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                            {S.drag_drop_pdf}
                        </span>
                    </div>
                )}
            </div>

            {error && (
                <div className="alert alert-danger" style={{ marginTop: '12px' }}>
                    <AlertCircle size={16} />
                    <span>{error}</span>
                </div>
            )}

            {cvData && !loading && (
                <CvProfile cvData={cvData} lang={lang} />
            )}

            <AdComponent />
        </div>
    );
}

export default FreelanceCvAnalyzer;