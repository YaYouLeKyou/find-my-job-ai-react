import React, { useState, useEffect } from 'react';
import { User, Trash2, Clock, Briefcase, FileText } from 'lucide-react';
import { LANGS, STRINGS } from '../../utils/translations';

const STORAGE_KEY = 'analyzed_cvs';

function loadAnalyzedCvs() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveAnalyzedCvs(cvs) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cvs));
}

export default function AnalyzedCvMemory({ lang, cvs, onRemove, onClear, onReanalyze }) {
    const S = STRINGS[LANGS[lang]?.code || 'fr'];
    const displayCvs = Array.isArray(cvs) ? cvs : [];

    const handleRemove = (id) => {
        if (onRemove) onRemove(id);
    };

    const formatDate = (ts) => {
        if (!ts) return '';
        const d = new Date(ts);
        return d.toLocaleDateString(LANGS[lang]?.code === 'en' ? 'en-US' : 'fr-FR', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    if (!displayCvs.length) {
        return (
            <div className="card" style={{
                background: 'var(--color-surface)',
                border: '1px dashed var(--color-border)',
                padding: '24px',
                textAlign: 'center',
            }}>
                <div style={{ marginBottom: '12px', opacity: 0.5 }}>
                    <FileText size={40} />
                </div>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-primary)', margin: '0 0 8px' }}>
                    {S.no_analyzed_cv}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', margin: 0 }}>
                    {S.no_analyzed_cv_desc}
                </p>
            </div>
        );
    }

    return (
        <div className="card" style={{ background: 'var(--color-surface)' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
            }}>
                <span style={{ fontSize: '1rem' }}>📄</span>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>
                    {S.analyzed_cvs || 'CV analysés en mémoire'}
                </h3>
                <span style={{
                    marginLeft: 'auto',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                    background: 'var(--color-surface-secondary)',
                    padding: '2px 10px',
                    borderRadius: '9999px',
                }}>
                    {displayCvs.length}
                </span>
                {onClear && displayCvs.length > 0 && (
                    <button
                        onClick={onClear}
                        style={{
                            marginLeft: '8px',
                            padding: '4px 10px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--color-border)',
                            background: 'var(--color-surface)',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            color: '#ef4444',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                        }}
                    >
                        <Trash2 size={12} />
                        {S.clear_all}
                    </button>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {displayCvs.map((cv) => (
                    <div key={cv.id} className="analyzed-cv-item" style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '12px 14px',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm)',
                    }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: 'var(--radius-sm)',
                            background: 'rgba(124, 77, 255, 0.1)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                        }}>
                            <User size={18} style={{ color: 'var(--primary-color)' }} />
                        </div>

                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{
                                fontSize: '0.9rem',
                                fontWeight: 700,
                                color: 'var(--color-text-primary)',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                            }}>
                                {cv.nom_complet || cv.fileName || 'CV'}
                            </div>
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                fontSize: '0.78rem',
                                color: 'var(--color-text-secondary)',
                                marginTop: '3px',
                            }}>
                                {cv.metier && (
                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                        <Briefcase size={12} />
                                        {cv.metier}
                                    </span>
                                )}
                                {cv.annees_experience && (
                                    <span>{cv.annees_experience} {S.years || 'ans'}</span>
                                )}
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                    <Clock size={12} />
                                    {formatDate(cv.analyzedAt)}
                                </span>
                            </div>
                        </div>

                         <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                             {onReanalyze && (
                                 <button
                                     onClick={() => onReanalyze(cv)}
                                     style={{
                                         padding: '6px',
                                         borderRadius: 'var(--radius-sm)',
                                         border: '1px solid var(--color-border)',
                                         background: 'var(--color-surface)',
                                         cursor: 'pointer',
                                         color: 'var(--color-text-secondary)',
                                         display: 'flex',
                                         alignItems: 'center',
                                         justifyContent: 'center',
                                     }}
                                     title={S.reanalyze}
                                 >
                                     <FileText size={14} />
                                 </button>
                             )}
                             <button
                                 onClick={() => handleRemove(cv.id)}
                                 style={{
                                     padding: '6px',
                                     borderRadius: 'var(--radius-sm)',
                                     border: '1px solid var(--color-border)',
                                     background: 'var(--color-surface)',
                                     cursor: 'pointer',
                                     color: '#ef4444',
                                     display: 'flex',
                                     alignItems: 'center',
                                     justifyContent: 'center',
                                 }}
                                 title={S.delete}
                             >
                                 <Trash2 size={14} />
                             </button>
                         </div>
<task_progress>
- [x] Analyze frontend structure and identify relevant files
- [x] Fix layout issues (button positioning, title alignment)
- [x] Remove duplicate trash icon in CV analysis
- [ ] Fix AI mode activation on mobile
- [ ] Test all changes
</task_progress>
                    </div>
                ))}
            </div>
        </div>
    );
}
