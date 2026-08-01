/**
 * AIChatDrawer - Chat AI Copilote flottant (Context-Aware)
 *
 * Composant flottant en bas à droite :
 *   - Bouton d'activation (FAB) + Tiroir/Drawer amovible
 *   - États : isOpen, messages, isLoading
 *   - Envoi des clés utilisateur dans les en-têtes HTTP (X-User-Gemini-Key, X-User-Groq-Key)
 *   - Auto-scroll automatique en bas
 *   - Contexte : agent_type, system_status, user_profile, displayed_jobs_summary
 *
 * Props :
 *   - jobs: array des offres affichées à l'écran
 *   - cvData: données du CV analysé (ou null)
 *   - agentType: 'job' | 'freelance' | 'recruiter'
 *   - noAiMode: boolean
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X, Send, Bot, User, Loader2, Sparkles } from 'lucide-react';
import { useAI } from '../context/AIContext';
import { LANGS, STRINGS } from '../utils/translations';

const API_BASE = import.meta.env.VITE_API_URL || '';

// ─── Quick suggestion prompts ─────────────────────────────────────────────────
const QUICK_PROMPTS = [
    { icon: '📊', text: "Analyse la première offre affichée" },
    { icon: '✍️', text: "Rédige un message d'approche pour ma candidature" },
    { icon: '💡', text: "Comment améliorer mon CV ?" },
    { icon: '⚙️', text: "Comment configurer ma clé API Gemini ?" },
];

// ─── Helper: Build job summaries from displayed jobs ──────────────────────────
function buildJobsSummary(jobs, maxJobs = 10) {
    if (!jobs || jobs.length === 0) return [];
    return jobs.slice(0, maxJobs).map(job => ({
        title: job.title || job.titre || '',
        company: job.company || job.entreprise || '',
        location: job.location || '',
        snippet: (job.description || job.snippet || '').substring(0, 200),
    }));
}

// ─── Helper: Build user profile from CV data ──────────────────────────────────
function buildUserProfile(cvData) {
    if (!cvData) return { skills: [], title: '' };
    return {
        skills: cvData.mots_cles || cvData.skills || [],
        title: cvData.metier || cvData.title || '',
    };
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function AIChatDrawer({ jobs = [], cvData = null, agentType = 'job', noAiMode = false, lang = 'Français' }) {
    const S = STRINGS[LANGS[lang]?.code || 'fr'];
    const { apiKeys, activeProvider } = useAI();
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: "👋 Salut ! Je suis ton Copilote AI. Je peux t'aider à analyser les offres affichées, conseiller sur ton CV, rédiger des messages d'approche, ou te guider sur l'utilisation de l'application. Comment puis-je t'aider ?",
            timestamp: Date.now(),
        },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    const scrollContainerRef = useRef(null);

    // ─── Auto-scroll to bottom on new messages ────────────────────────────────
    const scrollToBottom = useCallback(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
        }
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    // ─── Focus input when drawer opens ────────────────────────────────────────
    useEffect(() => {
        if (isOpen && inputRef.current) {
            setTimeout(() => inputRef.current?.focus(), 300);
        }
    }, [isOpen]);

    // ─── Build context payload ────────────────────────────────────────────────
    const buildContext = useCallback(() => {
        const userGeminiKey = apiKeys.gemini?.key || '';
        const userGroqKey = apiKeys.groq?.key || '';

        return {
            agent_type: agentType,
            system_status: {
                user_gemini_configured: !!userGeminiKey,
                user_groq_configured: !!userGroqKey,
                no_ai_mode: noAiMode,
            },
            user_profile: buildUserProfile(cvData),
            displayed_jobs_summary: buildJobsSummary(jobs),
        };
    }, [apiKeys, agentType, cvData, jobs, noAiMode]);

    // ─── Send message to backend ──────────────────────────────────────────────
    const sendMessage = useCallback(async (messageText) => {
        const text = (messageText || input).trim();
        if (!text || isLoading) return;

        // Add user message
        const userMessage = { role: 'user', content: text, timestamp: Date.now() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            // Build headers with user API keys (security: never in body)
            const headers = {
                'Content-Type': 'application/json',
            };
            const userGeminiKey = apiKeys.gemini?.key || '';
            const userGroqKey = apiKeys.groq?.key || '';
            if (userGeminiKey) headers['X-User-Gemini-Key'] = userGeminiKey;
            if (userGroqKey) headers['X-User-Groq-Key'] = userGroqKey;

            // Build payload
            const payload = {
                message: text,
                context: buildContext(),
            };

            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            const assistantMessage = {
                role: 'assistant',
                content: data.response || "Désolé, je n'ai pas pu générer de réponse.",
                timestamp: Date.now(),
                provider: data.provider_used,
                quotaExhausted: data.quota_exhausted,
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('[AIChatDrawer] Error:', error);
            const errorMessage = {
                role: 'assistant',
                content: `🤖 Désolé, une erreur est survenue (${error.message}). Vérifie que le backend est démarré et réessaie.`,
                timestamp: Date.now(),
                isError: true,
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    }, [apiKeys, buildContext, input, isLoading]);

    // ─── Handle Enter key (send) ──────────────────────────────────────────────
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // ─── Quick prompt click ───────────────────────────────────────────────────
    const handleQuickPrompt = (promptText) => {
        sendMessage(promptText);
    };

    // ─── Render message bubble ────────────────────────────────────────────────
    const renderMessage = (msg, idx) => {
        const isUser = msg.role === 'user';
        return (
            <div
                key={idx}
                style={{
                    display: 'flex',
                    gap: '10px',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    marginBottom: '16px',
                    animation: 'chatFadeIn 0.3s ease',
                }}
            >
                {/* Avatar */}
                <div style={{
                    flexShrink: 0,
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isUser
                        ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                        : msg.isError
                            ? 'linear-gradient(135deg, #ef4444, #f97316)'
                            : 'linear-gradient(135deg, #10b981, #06b6d4)',
                    color: '#fff',
                }}>
                    {isUser ? <User size={16} /> : msg.isError ? <X size={16} /> : <Bot size={16} />}
                </div>

                {/* Bubble */}
                <div style={{
                    maxWidth: '80%',
                    padding: '12px 16px',
                    borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    background: isUser
                        ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                        : msg.isError
                            ? 'rgba(239, 68, 68, 0.1)'
                            : 'var(--color-surface, #f1f5f9)',
                    color: isUser ? '#fff' : 'var(--color-text-primary, #1e293b)',
                    border: msg.isError ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--color-border, transparent)',
                    fontSize: '0.875rem',
                    lineHeight: '1.5',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                }}>
                    {msg.content}
                    {msg.provider && msg.provider !== 'none' && (
                        <div style={{
                            marginTop: '8px',
                            fontSize: '0.7rem',
                            opacity: 0.6,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                        }}>
                            <Sparkles size={10} />
                            {msg.provider === 'user_gemini' && 'via Gemini (ta clé)'}
                            {msg.provider === 'user_groq' && 'via Groq (ta clé)'}
                            {msg.provider === 'server_groq' && 'via Groq (serveur)'}
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <>
            {/* ─── Floating Action Button (FAB) ──────────────────────────────── */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    aria-label={S.copilot_ai}
                    style={{
                        position: 'fixed',
                        bottom: '24px',
                        right: '24px',
                        zIndex: 9998,
                        height: '56px',
                        padding: '0 18px',
                        borderRadius: '9999px',
                        border: 'none',
                        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                        color: '#fff',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        boxShadow: '0 4px 20px rgba(99, 102, 241, 0.4)',
                        transition: 'all 0.3s ease',
                        animation: 'chatPulse 2s infinite',
                        fontSize: '0.95rem',
                        fontWeight: 700,
                        fontFamily: 'var(--font-sans)',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.05)';
                        e.currentTarget.style.boxShadow = '0 6px 28px rgba(99, 102, 241, 0.5)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'scale(1)';
                        e.currentTarget.style.boxShadow = '0 4px 20px rgba(99, 102, 241, 0.4)';
                    }}
                >
                    <MessageCircle size={20} />
                    <span>{S.copilot_ai}</span>
                    {/* Notification dot */}
                    <span style={{
                        position: 'absolute',
                        top: '4px',
                        right: '4px',
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        background: '#10b981',
                        border: '2px solid #fff',
                    }} />
                </button>
            )}

            {/* ─── Chat Drawer ────────────────────────────────────────────────── */}
            {isOpen && (
                <div
                    style={{
                        position: 'fixed',
                        bottom: '0',
                        right: '0',
                        zIndex: 9999,
                        width: '100%',
                        maxWidth: '420px',
                        height: 'min(640px, 90vh)',
                        display: 'flex',
                        flexDirection: 'column',
                        background: 'var(--color-bg, #ffffff)',
                        boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.15)',
                        borderLeft: '1px solid var(--color-border, #e2e8f0)',
                        borderTop: '1px solid var(--color-border, #e2e8f0)',
                        borderRadius: '16px 0 0 0',
                        animation: 'chatSlideUp 0.3s ease',
                        overflow: 'hidden',
                    }}
                >
                    {/* ─── Header ──────────────────────────────────────────────── */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '14px 18px',
                        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                        color: '#fff',
                        flexShrink: 0,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '50%',
                                background: 'rgba(255,255,255,0.2)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}>
                                <Bot size={20} />
                            </div>
                            <div>
                                <div style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                                    Copilote AI
                                </div>
                                <div style={{
                                    fontSize: '0.7rem',
                                    opacity: 0.85,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                }}>
                                    <span style={{
                                        width: '6px',
                                        height: '6px',
                                        borderRadius: '50%',
                                        background: '#10b981',
                                        display: 'inline-block',
                                    }} />
                                    Context-Aware · {jobs.length} offre{jobs.length !== 1 ? 's' : ''} à l'écran
                                </div>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            aria-label="Fermer le chat"
                            style={{
                                background: 'rgba(255,255,255,0.15)',
                                border: 'none',
                                color: '#fff',
                                cursor: 'pointer',
                                padding: '6px',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'background 0.2s',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.25)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.15)'}
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {/* ─── Messages Container ──────────────────────────────────── */}
                    <div
                        ref={scrollContainerRef}
                        style={{
                            flex: 1,
                            overflowY: 'auto',
                            padding: '18px',
                            background: 'var(--color-bg-secondary, #f8fafc)',
                        }}
                    >
                        {messages.map((msg, idx) => renderMessage(msg, idx))}

                        {/* Loading indicator */}
                        {isLoading && (
                            <div style={{
                                display: 'flex',
                                gap: '10px',
                                marginBottom: '16px',
                            }}>
                                <div style={{
                                    flexShrink: 0,
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                                    color: '#fff',
                                }}>
                                    <Bot size={16} />
                                </div>
                                <div style={{
                                    padding: '12px 16px',
                                    borderRadius: '18px 18px 18px 4px',
                                    background: 'var(--color-surface, #f1f5f9)',
                                    border: '1px solid var(--color-border, transparent)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    fontSize: '0.875rem',
                                    color: 'var(--color-text-secondary, #64748b)',
                                }}>
                                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                                    <span>Le Copilote réfléchit...</span>
                                </div>
                            </div>
                        )}

                        {/* Quick prompts (only shown when few messages) */}
                        {messages.length <= 1 && !isLoading && (
                            <div style={{
                                marginTop: '20px',
                                padding: '16px',
                                background: 'var(--color-surface, #f1f5f9)',
                                borderRadius: '12px',
                                border: '1px solid var(--color-border, #e2e8f0)',
                            }}>
                                <div style={{
                                    fontSize: '0.75rem',
                                    fontWeight: 600,
                                    color: 'var(--color-text-secondary, #64748b)',
                                    marginBottom: '10px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                }}>
                                    💡 Suggestions rapides
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    {QUICK_PROMPTS.map((prompt, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => handleQuickPrompt(prompt.text)}
                                            style={{
                                                textAlign: 'left',
                                                padding: '10px 14px',
                                                borderRadius: '10px',
                                                border: '1px solid var(--color-border, #e2e8f0)',
                                                background: 'var(--color-bg, #fff)',
                                color: 'var(--color-text-primary, #1e293b)',
                                                cursor: 'pointer',
                                                fontSize: '0.825rem',
                                                fontWeight: 500,
                                                transition: 'all 0.2s',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.borderColor = '#6366f1';
                                                e.currentTarget.style.background = 'rgba(99, 102, 241, 0.05)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.borderColor = 'var(--color-border, #e2e8f0)';
                                                e.currentTarget.style.background = 'var(--color-bg, #fff)';
                                            }}
                                        >
                                            <span style={{ fontSize: '1rem' }}>{prompt.icon}</span>
                                            {prompt.text}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* ─── Input Area ──────────────────────────────────────────── */}
                    <div style={{
                        flexShrink: 0,
                        padding: '14px 18px',
                        background: 'var(--color-bg, #fff)',
                        borderTop: '1px solid var(--color-border, #e2e8f0)',
                    }}>
                        <div style={{
                            display: 'flex',
                            gap: '10px',
                            alignItems: 'flex-end',
                        }}>
                            <textarea
                                ref={inputRef}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Pose ta question..."
                                rows={1}
                                disabled={isLoading}
                                style={{
                                    flex: 1,
                                    padding: '10px 14px',
                                    borderRadius: '12px',
                                    border: '1px solid var(--color-border, #e2e8f0)',
                                    background: 'var(--color-surface, #f8fafc)',
                                    color: 'var(--color-text-primary, #1e293b)',
                                    fontSize: '0.875rem',
                                    fontFamily: 'inherit',
                                    resize: 'none',
                                    outline: 'none',
                                    maxHeight: '100px',
                                    minHeight: '42px',
                                    transition: 'border-color 0.2s',
                                    opacity: isLoading ? 0.6 : 1,
                                }}
                                onFocus={(e) => {
                                    e.currentTarget.style.borderColor = '#6366f1';
                                    e.currentTarget.style.boxShadow = '0 0 0 2px rgba(99, 102, 241, 0.15)';
                                }}
                                onBlur={(e) => {
                                    e.currentTarget.style.borderColor = 'var(--color-border, #e2e8f0)';
                                    e.currentTarget.style.boxShadow = 'none';
                                }}
                            />
                            <button
                                onClick={() => sendMessage()}
                                disabled={!input.trim() || isLoading}
                                aria-label="Envoyer le message"
                                style={{
                                    width: '42px',
                                    height: '42px',
                                    flexShrink: 0,
                                    borderRadius: '12px',
                                    border: 'none',
                                    background: input.trim() && !isLoading
                                        ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                                        : 'var(--color-surface-hover, #e2e8f0)',
                                    color: input.trim() && !isLoading ? '#fff' : 'var(--color-text-muted, #94a3b8)',
                                    cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'all 0.2s',
                                }}
                            >
                                {isLoading ? (
                                    <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                                ) : (
                                    <Send size={18} />
                                )}
                            </button>
                        </div>
                        <div style={{
                            marginTop: '8px',
                            fontSize: '0.7rem',
                            color: 'var(--color-text-muted, #94a3b8)',
                            textAlign: 'center',
                        }}>
                            Le Copilote est conscient du contexte (offres, profil, statut IA)
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}