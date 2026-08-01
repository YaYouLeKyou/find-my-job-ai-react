/**
 * DocumentAnalyzer - Analyseur polymorphe (CV ou Fiche de poste)
 *
 * Ce composant est IDENTIQUE pour les 3 agents. Il gère :
 *   - L'upload de PDF (CV ou Fiche de poste)
 *   - L'analyse via l'API backend (/api/analyze-cv)
 *   - Le mode Sans IA (force_fallback_mode)
 *   - L'affichage du profil analysé (CvProfile)
 *
 * Le mode Sans IA est contrôlé par AgentContext (noAiMode).
 * Lorsqu'il est activé, force_fallback_mode est envoyé au backend.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Upload, AlertCircle, FileText, CheckCircle2, Loader2 } from 'lucide-react';
import { LANGS, STRINGS } from '../../utils/translations';
import { useAgent } from '../../context/AgentContext';
import { useAI } from '../../context/AIContext';
import CvProfile from '../CvProfile';
import AdComponent from '../AdComponent';

const API_BASE = import.meta.env.VITE_API_URL || '';

function DocumentAnalyzer({ lang, onAnalysisSuccess, cvData: externalCvData }) {
    const S = STRINGS[LANGS[lang].code];
    const { noAiMode } = useAgent();
    const { activeModel } = useAI();

    const [dragActive, setDragActive] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [fileName, setFileName] = useState('');
    const [cvData, setCvData] = useState(null);
    const fileInputRef = useRef(null);

    // Sync external cvData changes (e.g. from history reload)
    useEffect(() => {
        try {
            if (externalCvData && typeof externalCvData === 'object') {
                setCvData(externalCvData);
                setFileName(externalCvData.fileName || externalCvData.nom_complet || 'CV');
            }
        } catch (err) {
            console.error('[DocumentAnalyzer] Error syncing external cvData:', err);
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
        // Mode Sans IA → force fallback (regex parsing, no AI)
        formData.append('force_fallback_mode', noAiMode ? 'true' : 'false');

        try {
            const response = await fetch(`${API_BASE}/api/analyze-cv`, {
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
                        console.error('[DocumentAnalyzer] Error parsing error response:', e);
                    }
                } else if (responseText.includes('<!doctype') || responseText.includes('<html')) {
                    errorMessage = `${S.backend_not_accessible} ${API_BASE}`;
                }

                if (response.status === 400) {
                    errorMessage += "\n\nCauses possibles :\n- Le fichier n'est pas un PDF\n- Le fichier est vide\n- Le PDF ne contient pas de texte extractible\n- Le texte extrait est trop court (< 50 caractères)";
                }

                throw new Error(errorMessage);
            }

            if (!contentType || !contentType.includes('application/json')) {
                throw new Error(S.invalid_response);
            }

            const data = JSON.parse(responseText);

            if (data.is_fallback) {
                console.warn('[DocumentAnalyzer] MODE SECOURS = Le parsing regex a été utilisé, pas l\'IA');
            } else {
                console.info('[DocumentAnalyzer] MODE IA = L\'analyse IA a réussi');
            }

            setCvData(data);
            if (onAnalysisSuccess) {
                onAnalysisSuccess(data);
            }
        } catch (err) {
            console.error('[DocumentAnalyzer] Unexpected error:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            processFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            processFile(e.target.files[0]);
        }
    };

    const onButtonClick = () => {
        fileInputRef.current.click();
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
                className={`upload-card ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={onButtonClick}
                style={{
                    border: `2px dashed ${dragActive ? 'var(--primary-color)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '24px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    background: dragActive ? 'rgba(124,77,255,0.05)' : 'var(--surface-color)',
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    style={{ display: 'none' }}
                    accept=".pdf"
                    onChange={handleChange}
                />

                <div className="upload-icon" style={{ marginBottom: '12px' }}>
                    {loading ? (
                        <Loader2 size={48} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary-color)' }} />
                    ) : fileName ? (
                        <CheckCircle2 size={32} style={{ color: 'var(--success-color)' }} />
                    ) : (
                        <Upload size={32} style={{ color: 'var(--text-secondary)' }} />
                    )}
                </div>

                <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: '700', marginBottom: '4px' }}>
                        {fileName ? fileName : S.upload}
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {loading ? S.analyze : S.pdf_supported}
                    </p>
                </div>

                {noAiMode && (
                    <div style={{
                        marginTop: '8px',
                        padding: '6px 12px',
                        background: 'rgba(255, 111, 0, 0.1)',
                        border: '1px solid rgba(255, 111, 0, 0.25)',
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        color: '#e65100',
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                    }}>
                        {S.no_ai_fallback}
                    </div>
                )}
            </div>

            {error && (
                <div className="alert alert-danger" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px 16px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                }}>
                    <AlertCircle size={18} />
                    <span style={{ fontSize: '0.85rem' }}>{error}</span>
                </div>
            )}

            {loading && (
                <div style={{ marginTop: '16px' }}>
                    <div style={{
                        background: 'linear-gradient(135deg, rgba(124,77,255,0.12), rgba(68,138,255,0.08))',
                        border: '1px solid rgba(124, 77, 255, 0.3)',
                        padding: '16px',
                        borderRadius: 'var(--radius-md)',
                        marginBottom: '16px',
                        textAlign: 'center',
                        color: 'var(--text-primary)',
                        fontWeight: '600',
                        fontSize: '0.95rem',
                    }}>
                        {S.analyzing_document}
                    </div>
                    <AdComponent />
                </div>
            )}

            {fileName && !loading && !error && (
                <div className="alert alert-success" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px 16px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                }}>
                    <FileText size={18} />
                    <span>{S.analyze_success}</span>
                </div>
            )}

            {/* Affichage du profil analysé */}
            {cvData && (
                <CvProfile
                    lang={lang}
                    cvData={cvData}
                    onSelectJobQuery={(query) => {
                        if (onAnalysisSuccess) {
                            onAnalysisSuccess({ ...cvData, _selectedQuery: query });
                        }
                    }}
                />
            )}
        </div>
    );
}

export default DocumentAnalyzer;
