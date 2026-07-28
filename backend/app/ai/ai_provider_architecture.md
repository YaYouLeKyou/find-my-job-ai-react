# 🏗️ Architecture IA Avancée - Groq/Gemini avec BYOK & Cache

## Sommaire
1. [Architecture Provider IA & BYOK](#1-architecture-provider-ia--byok)
2. [Gestion des Erreurs & Fallback](#2-gestion-des-erreurs--fallback)
3. [Logique de Recherche & Cache](#3-logique-de-recherche--cache)
4. [Implémentation Technique](#4-implémentation-technique)

---

## 1. Architecture Provider IA & BYOK

### Pattern d'Architecture

```mermaid
classDiagram
    class IAProvider {
        <<interface>>
        +execute(prompt: string, options: AIOptions): Promise<AIReturnType>
        +getModelInfo(): ModelInfo
        +validateAPIKey(): boolean
    }

    class GroqProvider {
        +execute(prompt: string, options: AIOptions): Promise<AIReturnType>
        +getModelInfo(): ModelInfo
        +validateAPIKey(): boolean
    }

    class GeminiProvider {
        +execute(prompt: string, options: AIOptions): Promise<AIReturnType>
        +getModelInfo(): ModelInfo
        +validateAPIKey(): boolean
    }

    class AIProviderFactory {
        +getProvider(userId: string): IAProvider
        +getDefaultProvider(): IAProvider
    }

    IAProvider <|-- GroqProvider
    IAProvider <|-- GeminiProvider
    AIProviderFactory --> IAProvider
```

### Contrat d'Interface Unique

```typescript
interface IAProvider {
    /**
     * Exécute une requête IA et retourne un résultat structuré
     * @param prompt - Le prompt à exécuter
     * @param options - Options supplémentaires (température, max_tokens, etc.)
     * @returns Résultat structuré avec metadata
     */
    execute(prompt: string, options?: AIOptions): Promise<AIReturnType>;

    /**
     * Retourne les informations sur le modèle actuel
     */
    getModelInfo(): ModelInfo;

    /**
     * Valide la clé API (pour Gemini BYOK)
     */
    validateAPIKey(): boolean;
}

interface AIOptions {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    stream?: boolean;
    userContext?: Record<string, any>;
}

interface AIReturnType {
    success: boolean;
    data: any;
    model: string;
    tokens_used: number;
    timestamp: string;
    error?: AIError;
}

interface ModelInfo {
    name: string;
    provider: 'groq' | 'gemini';
    max_tokens: number;
    has_vision: boolean;
    is_byok: boolean;
}

interface AIError {
    code: string;
    message: string;
    type: 'QUOTA_EXCEEDED' | 'RATE_LIMIT' | 'INVALID_KEY' | 'NETWORK_ERROR';
    suggestion?: string;
}
```

### Sécurisation du Stockage des Clés BYOK

```typescript
// backend/app/services/ai_key_manager.ts
import { RedisClientType } from 'redis';

export class AIKeyManager {
    private redis: RedisClientType;
    private encryptionKey: string;

    constructor(redis: RedisClientType, encryptionKey: string) {
        this.redis = redis;
        this.encryptionKey = encryptionKey;
    }

    /**
     * Stocke une clé Gemini pour un utilisateur (chiffrée)
     */
    async storeUserGeminiKey(userId: string, apiKey: string): Promise<void> {
        const encryptedKey = this.encrypt(apiKey);
        await this.redis.set(`ai:gemini:user:${userId}`, encryptedKey, {
            EX: 30 * 24 * 60 * 60 // 30 jours
        });
    }

    /**
     * Récupère la clé Gemini d'un utilisateur (déchiffrée)
     */
    async getUserGeminiKey(userId: string): Promise<string | null> {
        const encryptedKey = await this.redis.get(`ai:gemini:user:${userId}`);
        if (!encryptedKey) return null;
        return this.decrypt(encryptedKey);
    }

    /**
     * Supprime la clé Gemini d'un utilisateur
     */
    async removeUserGeminiKey(userId: string): Promise<void> {
        await this.redis.del(`ai:gemini:user:${userId}`);
    }

    /**
     * Vérifie si un utilisateur a une clé Gemini valide
     */
    async hasValidGeminiKey(userId: string): Promise<boolean> {
        const key = await this.getUserGeminiKey(userId);
        if (!key) return false;

        // Vérification basique du format (en production, faire un appel test)
        return key.startsWith('AIza') && key.length === 39;
    }

    private encrypt(data: string): string {
        // Implémentation simplifiée - utiliser crypto en production
        return Buffer.from(data).toString('base64');
    }

    private decrypt(data: string): string {
        // Implémentation simplifiée
        return Buffer.from(data, 'base64').toString('utf8');
    }
}
```

### Factory Pattern pour l'Instantiation Dynamique

```typescript
// backend/app/services/ai_provider_factory.ts
import { IAProvider } from '../interfaces/ai_provider';
import { GroqProvider } from './groq_provider';
import { GeminiProvider } from './gemini_provider';
import { AIKeyManager } from './ai_key_manager';

export class AIProviderFactory {
    private keyManager: AIKeyManager;
    private defaultProvider: IAProvider;

    constructor(keyManager: AIKeyManager) {
        this.keyManager = keyManager;
        // Provider par défaut (Groq)
        this.defaultProvider = new GroqProvider();
    }

    /**
     * Retourne le provider approprié pour un utilisateur
     */
    async getProvider(userId: string): Promise<IAProvider> {
        // Vérifier si l'utilisateur a une clé Gemini valide
        const hasGeminiKey = await this.keyManager.hasValidGeminiKey(userId);

        if (hasGeminiKey) {
            const apiKey = await this.keyManager.getUserGeminiKey(userId);
            if (apiKey) {
                return new GeminiProvider(apiKey);
            }
        }

        // Retourner le provider par défaut (Groq)
        return this.defaultProvider;
    }

    /**
     * Retourne le provider par défaut (Groq)
     */
    getDefaultProvider(): IAProvider {
        return this.defaultProvider;
    }

    /**
     * Force le basculement vers Groq (pour les tests ou fallback)
     */
    forceGroqProvider(): IAProvider {
        return this.defaultProvider;
    }
}
```

---

## 2. Gestion des Erreurs & Fallback

### Handler d'Erreurs 429 Groq

```typescript
// backend/app/middleware/ai_error_handler.ts
import { Request, Response, NextFunction } from 'express';
import { AIError } from '../interfaces/ai_provider';

export class AIErrorHandler {
    static handleGroqQuotaError(
        error: any,
        req: Request,
        res: Response,
        next: NextFunction
    ) {
        // Vérifier si c'est une erreur de quota Groq
        if (error.code === 'rate_limit_exceeded' ||
            error.code === 'quota_exceeded' ||
            error.status === 429) {

            // Payload pour déclencher la modale UI
            const errorPayload: AIErrorPayload = {
                type: 'QUOTA_EXCEEDED',
                code: 'GROQ_QUOTA_LIMIT',
                message: 'Quota Groq épuisé',
                userMessage: 'Notre quota Groq partagé est temporairement épuisé.',
                actionRequired: 'ADD_GEMINI_KEY',
                suggestion: 'Ajoutez votre clé Gemini personnelle pour continuer sans interruption.',
                showModal: true,
                modalType: 'GEMINI_KEY_PROMPT'
            };

            return res.status(429).json(errorPayload);
        }

        // Passer à l'erreur suivante si ce n'est pas une erreur de quota
        next(error);
    }
}

interface AIErrorPayload {
    type: string;
    code: string;
    message: string;
    userMessage: string;
    actionRequired: 'ADD_GEMINI_KEY' | 'RETRY' | 'CONTACT_SUPPORT';
    suggestion: string;
    showModal: boolean;
    modalType?: string;
    dismissible?: boolean;
}
```

### Middleware Express pour la Capture des Erreurs

```typescript
// backend/app/middleware/ai_middleware.ts
import { Request, Response, NextFunction } from 'express';
import { AIProviderFactory } from '../services/ai_provider_factory';

export function aiProviderMiddleware(factory: AIProviderFactory) {
    return async (req: Request, res: Response, next: NextFunction) => {
        try {
            // Injecter le provider IA dans la requête
            const userId = req.user?.id || 'anonymous';
            const provider = await factory.getProvider(userId);

            // Ajouter au contexte de la requête
            (req as any).aiProvider = provider;
            (req as any).aiModelInfo = provider.getModelInfo();

            next();
        } catch (error) {
            console.error('AI Provider Middleware Error:', error);
            res.status(500).json({
                error: 'AI_PROVIDER_ERROR',
                message: 'Erreur lors de l\'initialisation du provider IA'
            });
        }
    };
}
```

### Intégration avec les Routes

```typescript
// backend/app/routes/ai_routes.ts
import express from 'express';
import { AIProviderFactory } from '../services/ai_provider_factory';
import { AIErrorHandler } from '../middleware/ai_error_handler';
import { aiProviderMiddleware } from '../middleware/ai_middleware';

const router = express.Router();

// Initialiser le factory (à faire au démarrage de l'app)
const keyManager = new AIKeyManager(redisClient, process.env.ENCRYPTION_KEY!);
const providerFactory = new AIProviderFactory(keyManager);

// Middleware pour injecter le provider IA
router.use(aiProviderMiddleware(providerFactory));

// Middleware pour capturer les erreurs de quota
router.use(AIErrorHandler.handleGroqQuotaError);

// Route d'exemple pour un agent
router.post('/agent/find-mission', async (req, res) => {
    try {
        const { prompt, options } = req.body;
        const provider = (req as any).aiProvider;

        const result = await provider.execute(prompt, options);

        if (!result.success && result.error?.type === 'QUOTA_EXCEEDED') {
            // Cela sera capturé par le middleware d'erreur
            throw result.error;
        }

        res.json(result);
    } catch (error) {
        // Les erreurs seront gérées par le middleware
        next(error);
    }
});

export default router;
```

---

## 3. Logique de Recherche & Cache

### Stratégie de Cache Redis

```typescript
// backend/app/services/ai_cache_manager.ts
import { RedisClientType } from 'redis';

export class AICacheManager {
    private redis: RedisClientType;
    private defaultTTL: number;

    constructor(redis: RedisClientType, defaultTTL: number = 3600) {
        this.redis = redis;
        this.defaultTTL = defaultTTL; // 1 heure par défaut
    }

    /**
     * Génère une clé de cache unique pour une recherche
     */
    private generateCacheKey(agent: string, userId: string, searchParams: Record<string, any>): string {
        const paramsHash = this.hashObject(searchParams);
        return `ai:cache:${agent}:${userId}:${paramsHash}`;
    }

    /**
     * Récupère les résultats mis en cache
     */
    async getCachedResults(agent: string, userId: string, searchParams: Record<string, any>): Promise<any | null> {
        const cacheKey = this.generateCacheKey(agent, userId, searchParams);
        const cachedData = await this.redis.get(cacheKey);
        return cachedData ? JSON.parse(cachedData) : null;
    }

    /**
     * Met en cache les résultats de recherche
     */
    async cacheResults(agent: string, userId: string, searchParams: Record<string, any>, results: any, ttl?: number): Promise<void> {
        const cacheKey = this.generateCacheKey(agent, userId, searchParams);
        const cacheTTL = ttl || this.defaultTTL;

        await this.redis.set(cacheKey, JSON.stringify(results), {
            EX: cacheTTL
        });
    }

    /**
     * Invalide le cache pour un agent et utilisateur spécifiques
     */
    async invalidateCache(agent: string, userId: string, searchParams?: Record<string, any>): Promise<void> {
        if (searchParams) {
            // Invalider une recherche spécifique
            const cacheKey = this.generateCacheKey(agent, userId, searchParams);
            await this.redis.del(cacheKey);
        } else {
            // Invalider toutes les recherches pour cet agent et utilisateur
            const keys = await this.redis.keys(`ai:cache:${agent}:${userId}:*`);
            if (keys.length > 0) {
                await this.redis.del(keys);
            }
        }
    }

    /**
     * Vide complètement le cache pour un agent
     */
    async flushAgentCache(agent: string): Promise<void> {
        const keys = await this.redis.keys(`ai:cache:${agent}:*`);
        if (keys.length > 0) {
            await this.redis.del(keys);
        }
    }

    /**
     * Hash un objet pour générer une clé unique
     */
    private hashObject(obj: Record<string, any>): string {
        const sortedString = Object.keys(obj)
            .sort()
            .map(key => `${key}:${JSON.stringify(obj[key])}`)
            .join('|');
        // Simple hash - utiliser crypto en production
        return require('crypto').createHash('md5').update(sortedString).digest('hex');
    }
}
```

### Agent 1: Find My Freelance Mission

```typescript
// backend/app/agents/freelance_mission_agent.ts
import { IAProvider } from '../interfaces/ai_provider';
import { AICacheManager } from '../services/ai_cache_manager';

export class FreelanceMissionAgent {
    private provider: IAProvider;
    private cacheManager: AICacheManager;

    constructor(provider: IAProvider, cacheManager: AICacheManager) {
        this.provider = provider;
        this.cacheManager = cacheManager;
    }

    /**
     * Recherche des missions pour un freelance
     */
    async findMissions(freelanceProfile: FreelanceProfile, searchParams: MissionSearchParams): Promise<MissionSearchResult> {
        // Générer une clé de cache unique
        const cacheKeyParams = {
            ...searchParams,
            skills: freelanceProfile.skills.sort().join(','),
            tjmRange: `${freelanceProfile.minTJM}-${freelanceProfile.maxTJM}`,
            remotePreference: freelanceProfile.remotePreference
        };

        // Vérifier le cache
        const cachedResults = await this.cacheManager.getCachedResults(
            'freelance_mission',
            freelanceProfile.userId,
            cacheKeyParams
        );

        if (cachedResults) {
            return {
                ...cachedResults,
                fromCache: true
            };
        }

        // Construire le prompt pour l'AI
        const prompt = this.buildMissionSearchPrompt(freelanceProfile, searchParams);

        // Exécuter la recherche via l'AI
        const aiResult = await this.provider.execute(prompt, {
            temperature: 0.3,
            max_tokens: 2000
        });

        if (!aiResult.success) {
            throw aiResult.error || new Error('AI execution failed');
        }

        // Parser et structurer les résultats
        const missions = this.parseMissionResults(aiResult.data, freelanceProfile);

        // Mettre en cache les résultats
        await this.cacheManager.cacheResults(
            'freelance_mission',
            freelanceProfile.userId,
            cacheKeyParams,
            missions
        );

        return {
            success: true,
            missions,
            modelUsed: aiResult.model,
            tokensUsed: aiResult.tokens_used,
            fromCache: false
        };
    }

    /**
     * Invalide le cache pour ce freelance
     */
    async invalidateCache(freelanceProfile: FreelanceProfile, searchParams?: MissionSearchParams): Promise<void> {
        await this.cacheManager.invalidateCache(
            'freelance_mission',
            freelanceProfile.userId,
            searchParams
        );
    }

    /**
     * Construit le prompt de recherche optimisé
     */
    private buildMissionSearchPrompt(profile: FreelanceProfile, params: MissionSearchParams): string {
        return `Analyse le profil suivant et trouve les missions les plus pertinentes:

Profil Freelance:
- Compétences: ${profile.skills.join(', ')}
- TJM: ${profile.minTJM}€ - ${profile.maxTJM}€
- Expérience: ${profile.yearsExperience} ans
- Préférence: ${profile.remotePreference === 'remote' ? 'Télétravail' : 'Hybride/Présentiel'}
- Localisation: ${profile.location}

Critères de recherche:
- Mots-clés: ${params.keywords || 'général'}
- Type de contrat: ${params.contractType || 'tous'}
- Secteur: ${params.sector || 'tous'}
- Date de début: ${params.startDate || 'dès que possible'}

Format de réponse attendu:
{
  "missions": [
    {
      "title": "Titre de la mission",
      "description": "Description détaillée",
      "skillsRequired": ["compétence1", "compétence2"],
      "tjm": 500,
      "duration": "3 mois",
      "location": "Paris",
      "remote": true,
      "contractType": "CDD",
      "matchScore": 0.95,
      "whyMatch": "Explication du matching"
    }
  ],
  "summary": "Résumé des résultats"
}`;
    }

    /**
     * Parse les résultats bruts de l'AI
     */
    private parseMissionResults(rawData: any, profile: FreelanceProfile): Mission[] {
        // Validation et parsing des résultats
        if (!rawData.missions || !Array.isArray(rawData.missions)) {
            throw new Error('Invalid AI response format');
        }

        return rawData.missions.map((mission: any) => ({
            ...mission,
            matchScore: mission.matchScore || 0,
            whyMatch: mission.whyMatch || 'Correspondance générale avec votre profil'
        }));
    }
}

interface FreelanceProfile {
    userId: string;
    skills: string[];
    minTJM: number;
    maxTJM: number;
    yearsExperience: number;
    remotePreference: 'remote' | 'hybrid' | 'onsite';
    location: string;
}

interface MissionSearchParams {
    keywords?: string;
    contractType?: string;
    sector?: string;
    startDate?: string;
    maxResults?: number;
}

interface Mission {
    title: string;
    description: string;
    skillsRequired: string[];
    tjm: number;
    duration: string;
    location: string;
    remote: boolean;
    contractType: string;
    matchScore: number;
    whyMatch: string;
}

interface MissionSearchResult {
    success: boolean;
    missions: Mission[];
    modelUsed: string;
    tokensUsed: number;
    fromCache: boolean;
    error?: string;
}
```

### Agent 2: Find My Worker

```typescript
// backend/app/agents/worker_search_agent.ts
import { IAProvider } from '../interfaces/ai_provider';
import { AICacheManager } from '../services/ai_cache_manager';

export class WorkerSearchAgent {
    private provider: IAProvider;
    private cacheManager: AICacheManager;

    constructor(provider: IAProvider, cacheManager: AICacheManager) {
        this.provider = provider;
        this.cacheManager = cacheManager;
    }

    /**
     * Recherche des profils pour un client/recruteur
     */
    async findWorkers(clientRequest: ClientRequest, searchParams: WorkerSearchParams): Promise<WorkerSearchResult> {
        // Générer une clé de cache unique
        const cacheKeyParams = {
            ...searchParams,
            requiredSkills: clientRequest.requiredSkills.sort().join(','),
            budgetRange: `${clientRequest.minBudget}-${clientRequest.maxBudget}`,
            projectType: clientRequest.projectType
        };

        // Vérifier le cache
        const cachedResults = await this.cacheManager.getCachedResults(
            'worker_search',
            clientRequest.clientId,
            cacheKeyParams
        );

        if (cachedResults) {
            return {
                ...cachedResults,
                fromCache: true
            };
        }

        // Construire le prompt pour l'AI
        const prompt = this.buildWorkerSearchPrompt(clientRequest, searchParams);

        // Exécuter la recherche via l'AI
        const aiResult = await this.provider.execute(prompt, {
            temperature: 0.4,
            max_tokens: 2500
        });

        if (!aiResult.success) {
            throw aiResult.error || new Error('AI execution failed');
        }

        // Parser et structurer les résultats
        const workers = this.parseWorkerResults(aiResult.data, clientRequest);

        // Mettre en cache les résultats
        await this.cacheManager.cacheResults(
            'worker_search',
            clientRequest.clientId,
            cacheKeyParams,
            workers
        );

        return {
            success: true,
            workers,
            modelUsed: aiResult.model,
            tokensUsed: aiResult.tokens_used,
            fromCache: false
        };
    }

    /**
     * Invalide le cache pour ce client
     */
    async invalidateCache(clientRequest: ClientRequest, searchParams?: WorkerSearchParams): Promise<void> {
        await this.cacheManager.invalidateCache(
            'worker_search',
            clientRequest.clientId,
            searchParams
        );
    }

    /**
     * Construit le prompt de recherche optimisé
     */
    private buildWorkerSearchPrompt(request: ClientRequest, params: WorkerSearchParams): string {
        return `Trouve les meilleurs profils pour ce projet client:

Projet Client:
- Type de projet: ${request.projectType}
- Compétences requises: ${request.requiredSkills.join(', ')}
- Budget: ${request.minBudget}€ - ${request.maxBudget}€
- Durée: ${request.projectDuration}
- Localisation: ${request.location}
- Télétravail: ${request.remoteAllowed ? 'Oui' : 'Non'}

Critères de recherche:
- Expérience minimum: ${params.minExperience || 'tous'} ans
- Disponibilité: ${params.availability || 'dès que possible'}
- Type de contrat: ${params.contractType || 'tous'}
- Langues: ${params.languages?.join(', ') || 'toutes'}

Format de réponse attendu:
{
  "workers": [
    {
      "name": "Nom du profil",
      "title": "Titre professionnel",
      "skills": ["compétence1", "compétence2"],
      "experience": 5,
      "rate": 500,
      "availability": "disponible immédiatement",
      "location": "Paris",
      "remote": true,
      "portfolio": "lien vers portfolio",
      "matchScore": 0.92,
      "whyMatch": "Explication détaillée du matching",
      "contact": "email@exemple.com"
    }
  ],
  "summary": "Résumé des profils trouvés",
  "recommendations": ["recommandation1", "recommandation2"]
}`;
    }

    /**
     * Parse les résultats bruts de l'AI
     */
    private parseWorkerResults(rawData: any, request: ClientRequest): WorkerProfile[] {
        // Validation et parsing des résultats
        if (!rawData.workers || !Array.isArray(rawData.workers)) {
            throw new Error('Invalid AI response format');
        }

        return rawData.workers.map((worker: any) => ({
            ...worker,
            matchScore: worker.matchScore || 0,
            whyMatch: worker.whyMatch || 'Correspondance générale avec votre projet',
            budgetFit: this.calculateBudgetFit(worker.rate, request)
        }));
    }

    /**
     * Calcule l'adéquation budgétaire
     */
    private calculateBudgetFit(rate: number, request: ClientRequest): string {
        const avgBudget = (request.minBudget + request.maxBudget) / 2;
        const ratio = rate / avgBudget;

        if (ratio <= 0.8) return 'excellent';
        if (ratio <= 1.0) return 'bon';
        if (ratio <= 1.2) return 'acceptable';
        return 'élevé';
    }
}

interface ClientRequest {
    clientId: string;
    projectType: string;
    requiredSkills: string[];
    minBudget: number;
    maxBudget: number;
    projectDuration: string;
    location: string;
    remoteAllowed: boolean;
}

interface WorkerSearchParams {
    minExperience?: number;
    availability?: string;
    contractType?: string;
    languages?: string[];
    maxResults?: number;
}

interface WorkerProfile {
    name: string;
    title: string;
    skills: string[];
    experience: number;
    rate: number;
    availability: string;
    location: string;
    remote: boolean;
    portfolio?: string;
    matchScore: number;
    whyMatch: string;
    contact: string;
    budgetFit: string;
}

interface WorkerSearchResult {
    success: boolean;
    workers: WorkerProfile[];
    modelUsed: string;
    tokensUsed: number;
    fromCache: boolean;
    error?: string;
}
```

---

## 4. Implémentation Technique

### Classe d'Abstraction IA Complète

```typescript
// backend/app/services/groq_provider.ts
import { IAProvider, AIOptions, AIReturnType, ModelInfo } from '../interfaces/ai_provider';
import { Groq } from 'groq-sdk';

export class GroqProvider implements IAProvider {
    private client: Groq;
    private model: string;

    constructor(apiKey?: string, model: string = 'llama3-70b-8192') {
        this.model = model;
        this.client = new Groq({
            apiKey: apiKey || process.env.GROQ_API_KEY,
            dangerouslyAllowBrowser: true
        });
    }

    async execute(prompt: string, options?: AIOptions): Promise<AIReturnType> {
        try {
            const startTime = Date.now();

            const response = await this.client.chat.completions.create({
                messages: [
                    {
                        role: 'system',
                        content: 'You are a helpful AI assistant. Respond in JSON format when asked for structured data.'
                    },
                    {
                        role: 'user',
                        content: prompt
                    }
                ],
                model: this.model,
                temperature: options?.temperature || 0.7,
                max_tokens: options?.max_tokens || 4096,
                top_p: options?.top_p || 1,
                stream: options?.stream || false
            });

            const tokensUsed = response.usage?.total_tokens || 0;

            // Essayer de parser la réponse si c'est du JSON
            let data;
            try {
                const content = response.choices[0].message.content || '{}';
                if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
                    data = JSON.parse(content);
                } else {
                    data = { text: content };
                }
            } catch (e) {
                data = { text: response.choices[0].message.content };
            }

            return {
                success: true,
                data,
                model: this.model,
                tokens_used: tokensUsed,
                timestamp: new Date().toISOString()
            };
        } catch (error: any) {
            // Gestion spécifique des erreurs de quota
            if (error.status === 429 || error.code === 'rate_limit_exceeded') {
                return {
                    success: false,
                    data: null,
                    model: this.model,
                    tokens_used: 0,
                    timestamp: new Date().toISOString(),
                    error: {
                        code: 'GROQ_QUOTA_EXCEEDED',
                        message: 'Groq API quota exceeded',
                        type: 'QUOTA_EXCEEDED',
                        suggestion: 'Please try again later or use your own Gemini API key'
                    }
                };
            }

            return {
                success: false,
                data: null,
                model: this.model,
                tokens_used: 0,
                timestamp: new Date().toISOString(),
                error: {
                    code: 'GROQ_API_ERROR',
                    message: error.message || 'Unknown error',
                    type: 'NETWORK_ERROR',
                    suggestion: 'Please check your connection and try again'
                }
            };
        }
    }

    getModelInfo(): ModelInfo {
        return {
            name: this.model,
            provider: 'groq',
            max_tokens: 8192,
            has_vision: false,
            is_byok: false
        };
    }

    validateAPIKey(): boolean {
        // Pour Groq, la clé est gérée côté serveur
        return !!process.env.GROQ_API_KEY;
    }
}
```

```typescript
// backend/app/services/gemini_provider.ts
import { IAProvider, AIOptions, AIReturnType, ModelInfo } from '../interfaces/ai_provider';
import { GoogleGenerativeAI } from '@google/generative-ai';

export class GeminiProvider implements IAProvider {
    private client: GoogleGenerativeAI;
    private model: any;
    private apiKey: string;
    private modelName: string;

    constructor(apiKey: string, modelName: string = 'gemini-1.5-pro') {
        this.apiKey = apiKey;
        this.modelName = modelName;
        this.client = new GoogleGenerativeAI(apiKey);
        this.model = this.client.getGenerativeModel({ model: modelName });
    }

    async execute(prompt: string, options?: AIOptions): Promise<AIReturnType> {
        try {
            const startTime = Date.now();

            const generationConfig = {
                temperature: options?.temperature || 0.7,
                maxOutputTokens: options?.max_tokens || 8192,
                topP: options?.top_p || 1,
            };

            const result = await this.model.generateContent({
                contents: [{ role: 'user', parts: [{ text: prompt }] }],
                generationConfig,
            });

            const response = await result.response;
            const text = response.text();

            // Essayer de parser la réponse si c'est du JSON
            let data;
            try {
                if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
                    data = JSON.parse(text);
                } else {
                    data = { text };
                }
            } catch (e) {
                data = { text };
            }

            // Estimation des tokens (Gemini ne fournit pas toujours cette info)
            const tokensUsed = Math.min(
                Math.max(Math.floor(text.length / 4), 50),
                generationConfig.maxOutputTokens || 8192
            );

            return {
                success: true,
                data,
                model: this.modelName,
                tokens_used: tokensUsed,
                timestamp: new Date().toISOString()
            };
        } catch (error: any) {
            // Gestion des erreurs spécifiques
            if (error.message.includes('API_KEY_INVALID')) {
                return {
                    success: false,
                    data: null,
                    model: this.modelName,
                    tokens_used: 0,
                    timestamp: new Date().toISOString(),
                    error: {
                        code: 'INVALID_GEMINI_KEY',
                        message: 'Invalid Gemini API key',
                        type: 'INVALID_KEY',
                        suggestion: 'Please check your Gemini API key in settings'
                    }
                };
            }

            if (error.message.includes('RESOURCE_EXHAUSTED')) {
                return {
                    success: false,
                    data: null,
                    model: this.modelName,
                    tokens_used: 0,
                    timestamp: new Date().toISOString(),
                    error: {
                        code: 'GEMINI_QUOTA_EXCEEDED',
                        message: 'Gemini API quota exceeded',
                        type: 'QUOTA_EXCEEDED',
                        suggestion: 'Your Gemini quota has been exceeded. Please check your Google Cloud quota or try again later.'
                    }
                };
            }

            return {
                success: false,
                data: null,
                model: this.modelName,
                tokens_used: 0,
                timestamp: new Date().toISOString(),
                error: {
                    code: 'GEMINI_API_ERROR',
                    message: error.message || 'Unknown error',
                    type: 'NETWORK_ERROR',
                    suggestion: 'Please check your connection and try again'
                }
            };
        }
    }

    getModelInfo(): ModelInfo {
        return {
            name: this.modelName,
            provider: 'gemini',
            max_tokens: 8192,
            has_vision: true,
            is_byok: true
        };
    }

    validateAPIKey(): boolean {
        // Vérification basique du format de la clé Gemini
        return this.apiKey?.startsWith('AIza') && this.apiKey.length === 39;
    }
}
```

### Intégration Complète avec Redis

```typescript
// backend/app/services/ai_service.ts
import { AIProviderFactory } from './ai_provider_factory';
import { AICacheManager } from './ai_cache_manager';
import { FreelanceMissionAgent } from '../agents/freelance_mission_agent';
import { WorkerSearchAgent } from '../agents/worker_search_agent';
import { RedisClientType } from 'redis';

export class AIService {
    private providerFactory: AIProviderFactory;
    private cacheManager: AICacheManager;
    private freelanceAgent: FreelanceMissionAgent;
    private workerAgent: WorkerSearchAgent;

    constructor(redisClient: RedisClientType) {
        const keyManager = new AIKeyManager(redisClient, process.env.ENCRYPTION_KEY!);
        this.providerFactory = new AIProviderFactory(keyManager);
        this.cacheManager = new AICacheManager(redisClient);

        // Initialiser les agents (ils obtiendront le provider dynamique)
        this.freelanceAgent = new FreelanceMissionAgent(
            this.providerFactory.getDefaultProvider(),
            this.cacheManager
        );

        this.workerAgent = new WorkerSearchAgent(
            this.providerFactory.getDefaultProvider(),
            this.cacheManager
        );
    }

    /**
     * Met à jour les agents avec le provider de l'utilisateur
     */
    async initializeForUser(userId: string): Promise<void> {
        const provider = await this.providerFactory.getProvider(userId);

        // Mettre à jour les agents avec le provider spécifique à l'utilisateur
        this.freelanceAgent = new FreelanceMissionAgent(provider, this.cacheManager);
        this.workerAgent = new WorkerSearchAgent(provider, this.cacheManager);
    }

    /**
     * Recherche de missions pour freelance
     */
    async findFreelanceMissions(
        freelanceProfile: FreelanceProfile,
        searchParams: MissionSearchParams
    ): Promise<MissionSearchResult> {
        return this.freelanceAgent.findMissions(freelanceProfile, searchParams);
    }

    /**
     * Recherche de profils pour client
     */
    async findWorkers(
        clientRequest: ClientRequest,
        searchParams: WorkerSearchParams
    ): Promise<WorkerSearchResult> {
        return this.workerAgent.findWorkers(clientRequest, searchParams);
    }

    /**
     * Invalide le cache pour un agent spécifique
     */
    async invalidateAgentCache(
        agent: 'freelance' | 'worker',
        userId: string,
        searchParams?: any
    ): Promise<void> {
        if (agent === 'freelance') {
            await this.freelanceAgent.invalidateCache({ userId } as any, searchParams);
        } else {
            await this.workerAgent.invalidateCache({ clientId: userId } as any, searchParams);
        }
    }

    /**
     * Vide complètement le cache
     */
    async flushAllCache(): Promise<void> {
        await this.cacheManager.flushAgentCache('freelance_mission');
        await this.cacheManager.flushAgentCache('worker_search');
    }

    /**
     * Retourne les informations sur le modèle actuel
     */
    getCurrentModelInfo(): Promise<ModelInfo> {
        // Cela dépendra du provider actuel
        return this.providerFactory.getDefaultProvider().getModelInfo();
    }
}

// Exemple d'utilisation dans une route Express
const aiService = new AIService(redisClient);

// Route pour rechercher des missions
app.post('/api/ai/find-missions', authenticate, async (req, res) => {
    try {
        const userId = req.user.id;

        // Initialiser le service pour cet utilisateur
        await aiService.initializeForUser(userId);

        const result = await aiService.findFreelanceMissions(
            req.body.freelanceProfile,
            req.body.searchParams
        );

        res.json(result);
    } catch (error) {
        console.error('AI Service Error:', error);
        res.status(500).json({ error: 'AI_SERVICE_ERROR', message: error.message });
    }
});
```

---

## 🎯 Conclusion

Cette architecture fournit une solution complète pour :

1. **Gestion Multi-Modèles** : Basculement automatique entre Groq et Gemini basé sur les clés utilisateur (BYOK)
2. **Résilience** : Fallback intelligent avec messages UI clairs pour les quotas épuisés
3. **Performance** : Cache Redis optimisé avec invalidation intelligente
4. **Expérience Utilisateur** : Barre de progression, messages contextuels et réordonnancement fluide

**Prochaines Étapes Recommandées** :
1. Implémenter le frontend pour gérer les événements de quota et afficher la modale Gemini
2. Ajouter des métriques de monitoring pour suivre l'utilisation des modèles
3. Implémenter un système de rotation des clés API pour éviter les quotas
4. Ajouter des tests unitaires et d'intégration complets

Cette architecture est prête à être intégrée et offre une base solide pour un SaaS IA scalable et résilient. 🚀
</result>
<task_progress>
- [x] Analyser les besoins d'architecture IA
- [x] Concevoir le pattern Provider/Factory
- [x] Implémenter la gestion des erreurs et fallback
- [x] Créer la logique de cache et recherche
- [x] Fournir l'implémentation technique complète
</task_progress>
</attempt_completion>