/**
 * ResultCard - Carte de résultat unifiée (Emploi / Mission / Candidat)
 *
 * Ce composant est IDENTIQUE pour les 3 agents. Il s'adapte dynamiquement
 * au type de résultat (job, mission, candidate) en fonction de l'agent
 * actif (agentConfig.resultType).
 */
import React, { useState } from 'react';
import {
    ExternalLink, Star, MapPin, Clock, Euro, Calendar,
    Building, Mail, Phone, FileText, Tag,
    ChevronDown, ChevronUp, Download, Loader2, Copy, Check,
    MessageSquare, Sparkles, Briefcase, Trash2,
} from 'lucide-react';
import { useAgent } from '../../context/AgentContext';
import { LANGS, STRINGS } from '../../utils/translations';

const API_BASE = import.meta.env.VITE_API_URL || '';

function ResultCard({
    item,
    resultType,
    onSave,
    onDelete,
    isSaved = false,
    aiScore,
    aiProcessed = false,
    cvData,
    rankingEngine,
    customGeminiKey,
    onStartInterview,
    lang = 'Français',
}) {
    const { agentConfig } = useAgent();
    const theme = agentConfig.theme;
    const primaryColor = theme.primary;

    const S = STRINGS[LANGS[lang]?.code || 'fr'];

    const [expanded, setExpanded] = useState(false);
    const [letterLoading, setLetterLoading] = useState(false);
    const [letterContent, setLetterContent] = useState('');
    const [letterError, setLetterError] = useState('');
    const [copied, setCopied] = useState(false);

    const title = item.title || item.poste || item.mission || item.name || S.untitled;
    const company = item.company || item.organisme || item.client || item.employer || '';
    const location = item.location || item.lieu || item.city || item.region || '';
    const description = item.description || item.resume || item.summary || item.desc || '';
    const link = item.link || item.url || item.source_url || '#';
    const date = item.date || item.published_date || item.created_at || '';
    const contract = item.contract || item.contract_type || item.type_contrat || '';
    const salary = item.salary || item.salaire || '';
    const duration = item.duration || item.mission_duration || '';
    const tjm = item.tjm || item.daily_rate || '';
    const email = item.email || '';
    const phone = item.phone || '';
    const skills = item.skills || item.competences || [];
    const source = item.source || '';

    const handleCopyLetter = async () => {
        if (!letterContent) return;
        try {
            await navigator.clipboard.writeText(letterContent);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const handleGenerateLetter = async () => {
        if (!cvData) return;
        setLetterLoading(true);
        setLetterError('');
        try {
            const response = await fetch(`${API_BASE}/api/generate-letter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cv_data: cvData,
                    job_title: title,
                    company: company,
                    job_description: description,
                    ranking_engine: rankingEngine,
                    custom_gemini_key: customGeminiKey || null,
                    lang_label: LANGS[lang]?.label || 'français',
                }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Échec de génération de la lettre.');
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
        const element = document.createElement('a');
        const file = new Blob([letterContent], { type: 'text/plain;charset=utf-8' });
        element.href = URL.createObjectURL(file);
        element.download = `lettre_${(company || 'entreprise').replace(/\s+/g, '_')}.txt`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    };

    const handleDeleteSource = () => {
        if (onDelete) {
            onDelete(item);
        }
    };

    const renderTypeSpecificFields = () => {
        switch (resultType) {
            case 'mission':
                return (
                    <>
                        {duration && (
                            <span style={metaChipStyle}>
                                <Clock size={12} />
                                <span>{duration}</span>
                            </span>
                        )}
                        {tjm && (
                            <span style={metaChipStyle}>
                                <Euro size={12} />
                                <span>TJM: {tjm}</span>
                            </span>
                        )}
                    </>
                );
            case 'candidate':
                return (
                    <>
                        {email && (
                            <span style={metaChipStyle}>
                                <Mail size={12} />
                                <span>{email}</span>
                            </span>
                        )}
                        {phone && (
                            <span style={metaChipStyle}>
                                <Phone size={12} />
                                <span>{phone}</span>
                            </span>
                        )}
                    </>
                );
            case 'job':
            default:
                return (
                    <>
                        {contract && (
                            <span style={metaChipStyle}>
                                <FileText size={12} />
                                <span>{contract}</span>
                            </span>
                        )}
                        {salary && (
                            <span style={metaChipStyle}>
                                <Euro size={12} />
                                <span>{salary}</span>
                            </span>
                        )}
                    </>
                );
        }
    };

    const renderSkills = () => {
        if (!skills || !Array.isArray(skills) || skills.length === 0) return null;
        return (
            <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                marginTop: '12px',
            }}>
                {skills.slice(0, 8).map((skill, idx) => (
                    <span key={idx} style={{
                        padding: '4px 10px',
                        background: `${primaryColor}12`,
                        color: primaryColor,
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        border: `1px solid ${primaryColor}20`,
                    }}>
                        {skill}
                    </span>
                ))}
                {skills.length > 8 && (
                    <span style={{
                        padding: '4px 10px',
                        color: 'var(--text-muted)',
                        fontSize: '0.75rem',
                    }}>
                        +{skills.length - 8}
                    </span>
                )}
            </div>
        );
    };

    const renderAiScore = () => {
        if (aiScore === undefined || aiScore === null) return null;
        const scoreNum = typeof aiScore === 'number' ? aiScore : parseInt(aiScore);
        if (isNaN(scoreNum)) return null;
        const isHigh = scoreNum >= 70;
        const isMedium = scoreNum >= 40;
        const scoreColor = isHigh ? '#10b981' : isMedium ? '#f59e0b' : '#ef4444';
        return (
            <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '9999px',
                background: `${scoreColor}15`,
                color: scoreColor,
                fontSize: '0.8rem',
                fontWeight: 700,
                border: `1px solid ${scoreColor}30`,
            }}>
                <span>🎯</span>
                <span>{scoreNum}%</span>
            </div>
        );
    };

    const metaChipStyle = {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        fontSize: '0.78rem',
        fontWeight: 500,
        color: 'var(--color-text-secondary)',
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm)',
    };

    const showLetterFeature = true;
    const showInterviewFeature = true;

    return (
        <div style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-secondary) 100%)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '24px',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
        }}
            onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
                e.currentTarget.style.transform = 'translateY(-3px)';
                e.currentTarget.style.borderColor = 'var(--color-primary-500)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.borderColor = 'var(--color-border)';
            }}
        >
            {/* Favorite star button - top right */}
            {onSave && (
                <div style={{
                    position: 'absolute',
                    top: '16px',
                    right: '16px',
                    zIndex: 2,
                }}>
                    <button
                        onClick={() => onSave(item)}
                        style={{
                            padding: '8px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--color-border)',
                            background: 'var(--color-surface)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.2s ease',
                            color: isSaved ? primaryColor : 'var(--color-text-muted)',
                            flexShrink: 0,
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--color-surface-hover)';
                            e.currentTarget.style.borderColor = isSaved ? primaryColor : 'var(--color-text-muted)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'var(--color-surface)';
                            e.currentTarget.style.borderColor = 'var(--color-border)';
                        }}
                        title={isSaved ? S.remove_favorite : S.add_favorite}
                    >
                        <Star
                            size={18}
                            fill={isSaved ? primaryColor : 'none'}
                            color={isSaved ? primaryColor : 'currentColor'}
                        />
                    </button>
                </div>
            )}

            {/* Header: Title + Company + AI Score */}
            <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: '12px',
                paddingRight: onSave ? '40px' : '0',
                marginTop: '8px',
            }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <h3 style={{
                        fontSize: '1.05rem',
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        margin: 0,
                        marginBottom: '6px',
                        lineHeight: '1.4',
                        letterSpacing: '-0.01em',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                    }}>
                        {title}
                    </h3>
                    {company && (
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: 'var(--color-primary-500)',
                        }}>
                            <Building size={14} />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{company}</span>
                        </div>
                    )}
                </div>
                {/* AI Score - inline with title */}
                <div style={{ flexShrink: 0, marginTop: '2px' }}>
                    {renderAiScore()}
                </div>
            </div>

            {/* Meta info with chips */}
            <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
            }}>
                {location && (
                    <span style={metaChipStyle}>
                        <MapPin size={12} />
                        <span>{location}</span>
                    </span>
                )}
                {date && (
                    <span style={metaChipStyle}>
                        <Calendar size={12} />
                        <span>{date}</span>
                    </span>
                )}
                {source && (
                    <div className="source-wrapper" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                        <span style={metaChipStyle}>
                            <Tag size={12} />
                            <span>{source}</span>
                        </span>
                        {source && (
                            <button
                                className="btn btn-delete-sm"
                                onClick={handleDeleteSource}
                                 title={S.delete_source}
                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#999' }}
                            >
                                <Trash2 size={14} />
                    </button>
                )}
                {/* Delete button */}
                {onDelete && (
                    <button
                        onClick={() => onDelete(item)}
                        style={{
                            padding: '8px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--color-border)',
                            background: 'var(--color-surface)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.2s ease',
                            color: 'var(--color-danger)',
                            flexShrink: 0,
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'var(--color-surface)';
                        }}
                         title={S.delete_offer}
                    >
                        <Trash2 size={18} />
                    </button>
                )}
            </div>
                )}
                {renderTypeSpecificFields()}
            </div>

            {/* Description */}
            {description && (
                <p style={{
                    fontSize: '0.85rem',
                    color: 'var(--color-text-secondary)',
                    margin: 0,
                    lineHeight: '1.7',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                }}>
                    {description}
                </p>
            )}

            {/* Skills */}
            {renderSkills()}

            {/* Actions: View link + Letter + Interview */}
            <div style={{
                display: 'flex',
                gap: '10px',
                marginTop: '8px',
                paddingTop: '16px',
                borderTop: '1px solid var(--color-border)',
                flexWrap: 'wrap',
            }}>
                <a
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                        flex: 1,
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        padding: '12px 16px',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        color: 'var(--color-primary-500)',
                        background: 'rgba(99, 102, 241, 0.08)',
                        border: '1px solid rgba(99, 102, 241, 0.15)',
                        borderRadius: 'var(--radius-sm)',
                        textDecoration: 'none',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        fontFamily: 'var(--font-sans)',
                        minWidth: '120px',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(99, 102, 241, 0.15)';
                        e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(99, 102, 241, 0.08)';
                        e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.15)';
                    }}
                >
                    {resultType === 'mission' ? '🌐 Voir la mission' : resultType === 'candidate' ? '🌐 Voir le profil' : "🌐 Voir l'offre"}
                    <ExternalLink size={14} />
                </a>

                {showLetterFeature && (
                    <button
                        onClick={() => setExpanded(!expanded)}
                        style={{
                            flex: 1,
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            padding: '12px 16px',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: 'white',
                            background: 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            fontFamily: 'var(--font-sans)',
                            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.25)',
                            minWidth: '120px',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.boxShadow = '0 6px 20px rgba(99, 102, 241, 0.35)';
                            e.currentTarget.style.transform = 'translateY(-1px)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.boxShadow = '0 4px 14px rgba(99, 102, 241, 0.25)';
                            e.currentTarget.style.transform = 'translateY(0)';
                        }}
                         title={S.ai_letter_title}
                    >
                        <FileText size={16} />
                        <span>Lettre IA</span>
                        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                )}

                {showInterviewFeature && onStartInterview && (
                    <button
                        onClick={() => onStartInterview(item)}
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            padding: '12px 16px',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: 'var(--color-text-primary)',
                            background: 'var(--color-surface)',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            fontFamily: 'var(--font-sans)',
                            minWidth: '100px',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--color-surface-hover)';
                            e.currentTarget.style.borderColor = 'var(--color-text-muted)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'var(--color-surface)';
                            e.currentTarget.style.borderColor = 'var(--color-border)';
                        }}
                         title={S.simulate_interview}
                    >
                        <MessageSquare size={16} />
                        <span>Entretien</span>
                    </button>
                )}
            </div>

            {/* Letter Expander */}
            {expanded && showLetterFeature && (
                <div style={{
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                    animation: 'slideUp 0.3s ease',
                }}>
                    {!cvData ? (
                        <div style={{
                            padding: '12px 16px',
                            background: 'rgba(239, 68, 68, 0.08)',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.85rem',
                            color: 'var(--color-error)',
                            fontWeight: 500,
                        }}>
                            Veuillez d'abord uploader votre CV pour générer la lettre.
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                                <button
                                    style={{
                                        flex: 1,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px',
                                        padding: '12px 20px',
                                        borderRadius: 'var(--radius-sm)',
                                        background: 'linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%)',
                                        color: 'white',
                                        border: 'none',
                                        cursor: letterLoading ? 'wait' : 'pointer',
                                        fontSize: '0.85rem',
                                        fontWeight: 600,
                                        opacity: letterLoading ? 0.7 : 1,
                                        fontFamily: 'var(--font-sans)',
                                        transition: 'all 0.2s ease',
                                    }}
                                    disabled={letterLoading}
                                    onClick={handleGenerateLetter}
                                >
                                    {letterLoading ? (
                                        <>
                                            <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                                            {S.letter_generating || 'Rédaction en cours...'}
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles size={16} />
                                            {S.generate_letter_btn || 'Générer la lettre (IA)'}
                                        </>
                                    )}
                                </button>
                                {letterContent && (
                                    <>
                                        <button
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '6px',
                                                padding: '12px 14px',
                                                borderRadius: 'var(--radius-sm)',
                                                border: '1px solid var(--color-border)',
                                                background: 'var(--color-surface)',
                                                color: 'var(--color-text-primary)',
                                                cursor: 'pointer',
                                                fontSize: '0.85rem',
                                                fontWeight: 600,
                                                fontFamily: 'var(--font-sans)',
                                                transition: 'all 0.2s ease',
                                            }}
                                            onClick={handleCopyLetter}
                                            title={S.copy_letter}
                                        >
                                            {copied ? <Check size={16} /> : <Copy size={16} />}
                                        </button>
                                        <button
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '6px',
                                                padding: '12px 14px',
                                                borderRadius: 'var(--radius-sm)',
                                                border: '1px solid var(--color-border)',
                                                background: 'var(--color-surface)',
                                                color: 'var(--color-text-primary)',
                                                cursor: 'pointer',
                                                fontSize: '0.85rem',
                                                fontWeight: 600,
                                                fontFamily: 'var(--font-sans)',
                                                transition: 'all 0.2s ease',
                                            }}
                                            onClick={handleDownload}
                                            title={S.download_letter_btn}
                                        >
                                            <Download size={16} />
                                        </button>
                                    </>
                                )}
                            </div>

                            {letterError && (
                                <div style={{
                                    padding: '12px 16px',
                                    background: 'rgba(239, 68, 68, 0.08)',
                                    border: '1px solid rgba(239, 68, 68, 0.2)',
                                    borderRadius: 'var(--radius-sm)',
                                    fontSize: '0.85rem',
                                    color: 'var(--color-error)',
                                    fontWeight: 500,
                                }}>
                                    {letterError}
                                </div>
                            )}

                            {letterContent && (
                                <div>
                                    <label style={{
                                        fontSize: '0.8rem',
                                        fontWeight: 600,
                                        color: 'var(--color-text-secondary)',
                                        marginBottom: '8px',
                                        display: 'block',
                                    }}>
                                        {S.letter_area_label || 'Votre lettre personnalisée :'}
                                    </label>
                                    <textarea
                                        style={{
                                            height: '300px',
                                            width: '100%',
                                            resize: 'vertical',
                                            padding: '14px',
                                            borderRadius: 'var(--radius-sm)',
                                            background: 'var(--color-surface)',
                                            border: '1px solid var(--color-border)',
                                            color: 'var(--color-text-primary)',
                                            fontSize: '0.85rem',
                                            lineHeight: '1.7',
                                            fontFamily: 'var(--font-sans)',
                                            outline: 'none',
                                        }}
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

export default ResultCard;