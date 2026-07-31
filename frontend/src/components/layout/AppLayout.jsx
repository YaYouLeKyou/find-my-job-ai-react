/**
 * AppLayout - Conteneur principal englobant Header + Sidebar + Main
 *
 * Ce composant est utilisé par tous les agents (Job Seeker, Freelance, Recruteur).
 * Il fournit la structure de base : Header en haut, Sidebar à gauche,
 * et un slot `children` pour le contenu principal.
 *
 * Le thème (couleurs) est automatiquement dérivé de l'agent actif
 * via agentsConfig.js.
 */
import React from 'react';
import Header from './Header';
import { useAgent } from '../../context/AgentContext';

export default function AppLayout({
    onBackToHub,
    lang,
    setLang,
    onToggleDarkMode,
    darkMode,
    children,
}) {
    const { agentConfig } = useAgent();

    return (
        <div className="app-container">
            {/* Header partagé - titre + no-AI toggle + dark mode + language */}
            <Header
                onBackToHub={onBackToHub}
                showAiToggle={true}
                onToggleDarkMode={onToggleDarkMode}
                darkMode={darkMode}
                lang={lang}
                setLang={setLang}
            />

            {/* Contenu principal */}
            <main className="main-content">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    {children}
                </div>
            </main>
        </div>
    );
}