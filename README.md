# 🚀 Find my work AI - Intelligent Job Search Assistant

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-19-cyan)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)

**Find my work AI** is an intelligent job search assistant that analyzes your CV, suggests career paths, and generates personalized cover letters using AI.

---

## ✨ Features

### 📄 CV Analysis
- PDF CV upload
- Automatic extraction of skills, experience, and job title
- Suggestions for compatible jobs and alternatives
- Personalized improvement tips

### 🔍 Multi-Source Job Search
- **LinkedIn, Indeed, Glassdoor, ZipRecruiter** (via JobSpy)
- **France Travail** (official API + scraping)
- **Google Jobs, Adzuna, Jooble, Apify**
- Advanced filters: contract type, remote work, location
- Sort by AI relevance, date, or proximity

### 🤖 Artificial Intelligence
- **AI ranking** of job offers by compatibility with your profile
- **Personalized cover letter** generation
- Multi-model support: Groq/Llama 3.3, Gemini 2.5/3.5, Ollama (local), xAI/Grok

### 🌍 Multilingual
- Interface available in **7 languages**: Français, English, Español, Deutsch, العربية, 日本語, 中文
- Automatic location adaptation

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance REST API
- **Groq** - Ultra-fast AI inference (Llama 3.3)
- **Google Gemini** - Advanced CV analysis
- **JobSpy** - Multi-platform job aggregation
- **Python 3.11+**

### Frontend
- **React 19** with Vite
- **Lucide React** - Modern icons
- **Modern CSS** - Responsive design and glassmorphism

### Alternative
- **Streamlit** - All-in-one standalone version

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm or yarn

### 1. Clone the repository

```bash
git clone git@github.com:YaYouLeKyou/find-my-job-ai-react.git
cd find-my-job-ai-react
```

### 2. Environment variables configuration

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
```

### 3. Backend Installation

```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### 4. Frontend Installation

```bash
cd frontend
npm install
cd ..
```

---

## 🚀 Getting Started

### Option 1: Streamlit Application (All-in-One)

```bash
python -m streamlit run main.py
```

Access **http://localhost:8501**

### Option 2: Backend + React Frontend

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

Access **http://localhost:5173**

---

## 📊 Project Architecture

```
find-my-job-ai-react/
├── main.py                    # Streamlit application (standalone)
├── backend/
│   ├── api.py                 # FastAPI API
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── utils/             # Translations and helpers
│   │   └── App.jsx            # Main application
│   ├── Dockerfile
│   └── nginx.conf
├── shared/                    # Shared code (Python)
│   ├── ai.py                  # AI provider calls
│   ├── jobs.py                # Job scraping and APIs
│   ├── utils.py               # Utilities (PDF, geoloc, etc.)
│   ├── translations.py        # Single source of truth for translations
│   └── tests/                 # Unit tests
├── docker-compose.yml
├── .env.example
└── DEPLOYMENT.md
```

---

## 🧪 Tests

```bash
# Unit tests
python -m unittest shared/tests/test_utils.py -v
```

**Result**: 12/12 tests passing ✅

---

## 🔑 Required API Keys

| Service | Key | Free | Registration |
|---------|-----|------|-------------|
| **Groq** | `GROQ_API_KEY` | ✅ Yes | [console.groq.com](https://console.groq.com) |
| **Gemini** | `GEMINI_API_KEY` | ✅ Yes | [aistudio.google.com](https://aistudio.google.com) |
| **France Travail** | `FRANCE_TRAVAIL_CLIENT_ID/SECRET` | ✅ Yes | [pole-emploi.fr](https://pole-emploi.fr) |
| **Adzuna** | `ADZUNA_APP_ID/KEY` | ✅ Yes | [adzuna.com](https://adzuna.com) |
| **SerpApi** | `SERPAPI_KEY` | 🆓 100 req/month | [serpapi.com](https://serpapi.com) |
| **Jooble** | `JOOBLE_API_KEY` | ✅ Yes | [jooble.org](https://jooble.org) |
| **Apify** | `APIFY_API_KEY` | 🆓 100$ credit | [apify.com](https://apify.com) |

---

## 🎯 Key Features for Users

1. **CV Upload** → Automatic AI analysis
2. **Job Selection** → Instant search on 10+ platforms
3. **Advanced Filters** → Full-time, Part-time, Internship, Apprenticeship, Remote
4. **AI Ranking** → Most relevant offers first
5. **Cover Letter** → Generated in 1 click, personalized and downloadable
6. **Direct Access** → Optimized links to platforms blocking AI

---

## 🛡️ Security

- ✅ Google authentication removed (no external dependency)
- ✅ Environment variables for all API keys
- ✅ Configurable CORS
- ✅ `.gitignore` protects sensitive files
- ✅ No user database (no personal data leakage)

---

## 📈 Roadmap

- [ ] Complete migration to `shared/` (full deduplication)
- [ ] Integration tests
- [ ] Support for more CV formats (DOCX, TXT)
- [ ] Search history
- [ ] Export results to CSV/PDF
- [ ] Dark/light mode
- [ ] Mobile app (React Native)

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the project
2. Create a branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT license. See `LICENSE` for more information.

---

## 👨‍💻 Author

**Yanès Hadiouche** - *Full Stack Developer*

---

## 📞 Contact

- **GitHub**: [@YaYouLeKyou](https://github.com/YaYouLeKyou)
- **Repository**: [find-my-job-ai-react](https://github.com/YaYouLeKyou/find-my-job-ai-react)
- **Email**: yanes75@hotmail.fr

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) for ultra-fast AI inference
- [Google Gemini](https://ai.google.dev) for CV analysis
- [JobSpy](https://github.com/sirfuzz/jobspy) for job aggregation
- [Streamlit](https://streamlit.io) for the UI framework
- [React](https://react.dev) and [Vite](https://vitejs.dev) for the frontend

---

## ⭐️ Support the project

If this project helps you in your job search, feel free to give it a ⭐️ on GitHub!

---

**Made with ❤️ and lots of ☕**