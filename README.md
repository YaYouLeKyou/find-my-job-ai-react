# 🚀 FindMyJobAI - Assistant de Recherche d'Emploi Intelligent

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-19-cyan)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)

**FindMyJobAI** est un assistant de recherche d'emploi intelligent qui analyse votre CV, suggère des pistes de carrière et génère des lettres de motivation personnalisées grâce à l'IA.

---

## ✨ Fonctionnalités

### 📄 Analyse de CV
- Upload de CV au format PDF
- Extraction automatique des compétences, expériences et métier
- Suggestions de métiers compatibles et alternatives
- Conseils d'amélioration personnalisés

### 🔍 Recherche d'Emploi Multi-Sources
- **LinkedIn, Indeed, Glassdoor, ZipRecruiter** (via JobSpy)
- **France Travail** (API officielle + scraping)
- **Google Jobs, Adzuna, Jooble, Apify**
- Filtres avancés : contrat, télétravail, localisation
- Tri par pertinence IA, date ou proximité

### 🤖 Intelligence Artificielle
- **Classement IA** des offres par compatibilité avec votre profil
- **Génération de lettres de motivation** personnalisées
- Support multi-modèles : Groq/Llama 3.3, Gemini 2.5/3.5, Ollama (local), xAI/Grok

### 🌍 Multilingue
- Interface disponible en **7 langues** : Français, English, Español, Deutsch, العربية, 日本語, 中文
- Adaptation automatique de la localisation

---

## 🛠️ Stack Technique

### Backend
- **FastAPI** - API REST haute performance
- **Groq** - Inference IA ultra-rapide (Llama 3.3)
- **Google Gemini** - Analyse de CV avancée
- **JobSpy** - Agrégation multi-plateformes
- **Python 3.11+**

### Frontend
- **React 19** avec Vite
- **Lucide React** - Icônes modernes
- **CSS moderne** - Design responsive et glassmorphism

### Alternative
- **Streamlit** - Version standalone tout-en-un

---

## 📦 Installation

### Prérequis
- Python 3.11+
- Node.js 20+
- npm ou yarn

### 1. Cloner le repository

```bash
git clone git@github.com:YaYouLeKyou/find-my-job-ai-react.git
cd find-my-job-ai-react
```

### 2. Configuration des variables d'environnement

```bash
cp .env.example .env
```

Éditez `.env` avec vos clés API :
```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
```

### 3. Installation du Backend

```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### 4. Installation du Frontend

```bash
cd frontend
npm install
cd ..
```

---

## 🚀 Démarrage

### Option 1: Application Streamlit (Tout-en-un)

```bash
python -m streamlit run main.py
```

Accédez à **http://localhost:8501**

### Option 2: Backend + Frontend React

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Accédez à **http://localhost:5173**

---

## 🐳 Déploiement avec Docker

```bash
# Configuration
cp .env.example .env
# Éditez .env avec vos clés API

# Lancement
docker-compose up -d

# Vérification
docker-compose ps
docker-compose logs -f
```

Accédez à **http://localhost**

📖 **Guide de déploiement détaillé** : [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📊 Architecture du Projet

```
find-my-job-ai-react/
├── main.py                    # Application Streamlit (standalone)
├── backend/
│   ├── api.py                 # API FastAPI
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # Composants React
│   │   ├── utils/             # Traductions et helpers
│   │   └── App.jsx            # Application principale
│   ├── Dockerfile
│   └── nginx.conf
├── shared/                    # Code partagé (Python)
│   ├── ai.py                  # Appels aux fournisseurs d'IA
│   ├── jobs.py                # Scraping et APIs d'emploi
│   ├── utils.py               # Utilitaires (PDF, géoloc, etc.)
│   ├── translations.py        # Traductions source unique
│   └── tests/                 # Tests unitaires
├── docker-compose.yml
├── .env.example
└── DEPLOYMENT.md
```

---

## 🧪 Tests

```bash
# Tests unitaires
python -m unittest shared/tests/test_utils.py -v
```

**Résultat** : 12/12 tests passent ✅

---

## 🔑 Clés API Requises

| Service | Clé | Gratuit | Inscription |
|---------|-----|---------|-------------|
| **Groq** | `GROQ_API_KEY` | ✅ Oui | [console.groq.com](https://console.groq.com) |
| **Gemini** | `GEMINI_API_KEY` | ✅ Oui | [aistudio.google.com](https://aistudio.google.com) |
| **France Travail** | `FRANCE_TRAVAIL_CLIENT_ID/SECRET` | ✅ Oui | [pole-emploi.fr](https://pole-emploi.fr) |
| **Adzuna** | `ADZUNA_APP_ID/KEY` | ✅ Oui | [adzuna.com](https://adzuna.com) |
| **SerpApi** | `SERPAPI_KEY` | 🆓 100 req/mois | [serpapi.com](https://serpapi.com) |
| **Jooble** | `JOOBLE_API_KEY` | ✅ Oui | [jooble.org](https://jooble.org) |
| **Apify** | `APIFY_API_KEY` | 🆓 100$ crédit | [apify.com](https://apify.com) |

---

## 🎯 Fonctionnalités Clés pour les Utilisateurs

1. **Upload de CV** → Analyse automatique par IA
2. **Sélection du métier** → Recherche instantanée sur 10+ plateformes
3. **Filtres avancés** → CDI, CDD, Stage, Alternance, Télétravail
4. **Classement IA** → Les offres les plus pertinentes en premier
5. **Lettre de motivation** → Générée en 1 clic, personnalisée et téléchargeable
6. **Accès direct** → Liens optimisés vers les plateformes bloquant l'IA

---

## 🛡️ Sécurité

- ✅ Authentification Google supprimée (pas de dépendance externe)
- ✅ Variables d'environnement pour toutes les clés API
- ✅ CORS configurable
- ✅ `.gitignore` protège les fichiers sensibles
- ✅ Pas de base de données utilisateur (pas de fuite de données personnelles)

---

## 📈 Roadmap

- [ ] Migration complète vers `shared/` (déduplication totale)
- [ ] Ajout de tests d'intégration
- [ ] Support de plus de formats de CV (DOCX, TXT)
- [ ] Historique des recherches
- [ ] Export des résultats en CSV/PDF
- [ ] Mode sombre/clair
- [ ] Application mobile (React Native)

---

## 🤝 Contribution

Les contributions sont les bienvenues ! 

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📄 License

Distribué sous la licence MIT. Voir `LICENSE` pour plus d'informations.

---

## 👨‍💻 Auteur

**Ounaïssa BENKASSEM** - *Développeur Full Stack*

---

## 📞 Contact

- **GitHub**: [@YaYouLeKyou](https://github.com/YaYouLeKyou)
- **Repository**: [find-my-job-ai-react](https://github.com/YaYouLeKyou/find-my-job-ai-react)
- **Email**: ounaissa.benkassem@gmail.com

---

## 🙏 Remerciements

- [Groq](https://groq.com) pour l'inférence IA ultra-rapide
- [Google Gemini](https://ai.google.dev) pour l'analyse de CV
- [JobSpy](https://github.com/sirfuzz/jobspy) pour l'agrégation d'offres
- [Streamlit](https://streamlit.io) pour le framework UI
- [React](https://react.dev) et [Vite](https://vitejs.dev) pour le frontend

---

## ⭐️ Supportez le projet

Si ce projet vous aide dans votre recherche d'emploi, n'hésitez pas à lui donner une ⭐️ sur GitHub !

---

**Fait avec ❤️ et beaucoup de ☕**