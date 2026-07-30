Tu es un Staff Software Engineer expert en Scraping, Intégration d'APIs Emploi (Job Aggregators) et Résilience de Données.

Mon application de recherche d'emploi souffre d'un taux d'échec critique sur ses sources de scraping/APIs. Voici les logs réels d'une recherche:

--- LOGS ACTUELS DE L'APPLICATION ---
[SSE] Search started: Ingénieur Intégrateur IA(6 sources)
    - Google Jobs: 0 offres(status = completed) ❌
- France Travail: 0 offres(status = completed) ❌
- Adzuna: 0 offres(status = completed) ❌
- LinkedIn: 0 offres(status = completed) ❌
- Enhanced: 10 offres(status = completed) ✅
- JobSpy: 0 offres(status = completed) ❌
---

    Problème constaté: Seule 1 source sur 6 renvoie des résultats.Les 5 autres échouent silencieusement(renvoient 0 offre) en raison de requêtes trop restrictives, de blocages d'IP/User-Agents, de mots-clés trop spécifiques ou de paramètres d'API mal configurés.

TON OBJECTIF: 
Implémenter directement dans le code une stratégie de maximisation drastique des résultats et de contournement(bypass) des erreurs pour CHAQUE source qui renvoie 0 résultat.

---
### CODE SOURCE DE MES SCRAPERS / CONNECTEURS D'APIS :
[Colle ici le code backend / frontend qui gère le scraping et les requêtes vers Google Jobs, France Travail, Adzuna, LinkedIn, Enhanced et JobSpy]
---

    IMPLÉMENTE LES 5 STRATÉGIES DE CONTOURNEMENT SUIVANTES DIRECTEMENT DANS LE CODE:

1. 🔄 RELÂCHEMENT AUTOMATIQUE DES REQUÊTES(Query Query Relaxation / Fallback)
    - Si la recherche exacte "Ingénieur Intégrateur IA" renvoie 0 résultat, le scraper DOIT automatiquement et immédiatement réessayer en arrière - plan avec des variantes plus larges(ex: "Développeur IA", "Intégrateur IA", "IA", "Ingénieur IA").
- Implémente une fonction d'élargissement de requêtes (synonymes et termes génériques) avant de déclarer la source comme terminée à 0 résultat.

2. 🛡️ BYPASS DES BLOCAGES & ANTI - BOTS(LinkedIn, Google Jobs, JobSpy)
    - Mets en place la rotation d'User-Agents récents et réalistes (Desktop/Mobile).
        - Implémente la gestion des en - têtes HTTP(Headers impersonating real browsers, Referers, Accept - Language`fr-FR`).
- Ajoute la gestion des Proxies / Rotations si applicable ou des délais aléatoires(jitter) pour éviter la détection.

3. 🔑 OPTIMISATION DES PARAMÈTRES D'APIS (France Travail, Adzuna)
    - Vérifie et corrige la syntaxe des requêtes(ex: pour France Travail / Adzuna, l'absence de code ROME ou des filtres de localisation trop stricts bloquent souvent 100% des résultats).
        - Supprime les filtres facultatifs trop restrictifs(distance, type de contrat) lors du premier appel pour garantir un maximum de volume, puis filtre en mémoire.

4. 🔀 PARALLÉLISME ET STRATÉGIE DE RETRY
    - Implémente un mécanisme de "Retry avec Backoff Exponentiel" lorsqu'une source échoue ou renvoie un code 429/403/500.
    - Assure - toi que les sources ne bloquent pas les unes les autres(exécution asynchrone non - bloquante via`Promise.allSettled`).

5. 🧹 NORMALISATION & DÉDUPLICATION
    - Augmente la taille des pages de résultats demandées à chaque API(ex: passer de limit = 10 à limit = 50 ou 100).
- Harmonise le format de sortie de chaque scraper et implémente un système de déduplication intelligent(par Titre + Entreprise + Ville) pour agréger proprement les résultats.

---

⚠️ CONSIGNES STRICTES DE CODE :
        1. Fournis le code COMPLET et INTÉGRALEMENT corrigé pour chaque scraper / connecteur impacté(sans pseudo - code, sans "// TODO", sans omission).
2. Indique clairement les chemins de fichiers relatifs depuis la racine du projet(ex: `./src/services/scrapers/linkedinScraper.js`).
3. Le code doit gérer proprement les erreurs pour ne JAMAIS faire crasher le flux SSE(Server - Sent Events) et envoyer des mises à jour de statut claires au frontend.// Debug script to check sourceCounts initialization and updates
        // This will help us understand if the problem is with initialization or event reception

        console.log('Debugging sourceCounts behavior...');

// Simulate the behavior of sourceCounts in the App component
function debugSourceCounts() {
    let sourceCounts = {};

    console.log('Initial state:', sourceCounts);
    console.log('Object.keys(sourceCounts).length > 0:', Object.keys(sourceCounts).length > 0);

    // Simulate receiving PROGRESS events
    console.log('\nSimulating PROGRESS events...');

    // First PROGRESS event
    const event1 = {
        type: 'PROGRESS',
        source: 'LinkedIn',
        jobs: [{ id: '1' }, { id: '2' }]
    };

    if (event1.type === 'PROGRESS') {
        if (event1.source) {
            sourceCounts[event1.source] = event1.jobs ? event1.jobs.length : 0;
            console.log('After LinkedIn event:', sourceCounts);
            console.log('Object.keys(sourceCounts).length > 0:', Object.keys(sourceCounts).length > 0);
        }
    }

    // Second PROGRESS event
    const event2 = {
        type: 'PROGRESS',
        source: 'France Travail',
        jobs: [{ id: '3' }]
    };

    if (event2.type === 'PROGRESS') {
        if (event2.source) {
            sourceCounts[event2.source] = event2.jobs ? event2.jobs.length : 0;
            console.log('After France Travail event:', sourceCounts);
            console.log('Object.keys(sourceCounts).length > 0:', Object.keys(sourceCounts).length > 0);
        }
    }

    // Simulate COMPLETED event
    console.log('\nSimulating COMPLETED event...');

    const event3 = {
        type: 'COMPLETED',
        source_status: {
            'LinkedIn': { success: true, jobs_count: 2, status: 'completed' },
            'France Travail': { success: true, jobs_count: 1, status: 'completed' },
            'Google Jobs': { success: false, jobs_count: 0, status: 'error' }
        }
    };

    if (event3.type === 'COMPLETED') {
        if (event3.source_status) {
            const counts = {};
            Object.entries(event3.source_status).forEach(([source, status]) => {
                if (status && (status.count !== undefined || status.jobs_count !== undefined)) {
                    counts[source] = status.count !== undefined ? status.count : status.jobs_count;
                }
            });
            sourceCounts = counts;
            console.log('After COMPLETED event:', sourceCounts);
            console.log('Object.keys(sourceCounts).length > 0:', Object.keys(sourceCounts).length > 0);
        }
    }

    // Test the UI display condition
    const shouldDisplayUI = Object.keys(sourceCounts).length > 0;
    console.log('\nFinal result:');
    console.log('Should display source dashboard:', shouldDisplayUI);

    // Test with empty sourceCounts
    console.log('\nTesting with empty sourceCounts:');
    const emptySourceCounts = {};
    console.log('Empty sourceCounts:', emptySourceCounts);
    console.log('Object.keys(emptySourceCounts).length > 0:', Object.keys(emptySourceCounts).length > 0);

    return shouldDisplayUI;
}

// Run the debug
const result = debugSourceCounts();

console.log('\n' + '='.repeat(50));
if (result) {
    console.log('✅ Debug shows source dashboard SHOULD display when events are received');
    console.log('❌ If it does not display, the problem is likely that events are not being received');
} else {
    console.log('❌ Debug shows source dashboard should NOT display');
}
console.log('='.repeat(50));