# 🚀 Guide de Déploiement Production - FindMyJobAI

## 📋 Table des matières
1. [Prérequis](#prérequis)
2. [Option 1: Déploiement avec Docker (Recommandé)](#option-1-déploiement-avec-docker)
3. [Option 2: Déploiement Manuel](#option-2-déploiement-manuel)
4. [Configuration des variables d'environnement](#configuration-des-variables-denvironnement)
5. [Nom de domaine et SSL](#nom-de-domaine-et-ssl)
6. [Monitoring et maintenance](#monitoring-et-maintenance)

---

## Prérequis

- Un serveur VPS (OVH, DigitalOcean, AWS, etc.) avec au moins **2GB RAM** et **1 CPU**
- Un nom de domaine (ex: `findmyjobai.com`)
- Accès SSH au serveur
- Docker et Docker Compose installés (pour l'option 1)

---

## Option 1: Déploiement avec Docker (Recommandé)

### 1.1. Cloner le repository

```bash
git clone git@github.com:YaYouLeKyou/find-my-job-ai-react.git
cd find-my-job-ai-react
```

### 1.2. Configurer les variables d'environnement

```bash
cp .env.example .env
nano .env  # Éditer avec vos vraies clés API
```

### 1.3. Lancer l'application

```bash
# Démarrer tous les services (backend + frontend)
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Vérifier le statut
docker-compose ps
```

### 1.4. Accéder à l'application

- **Frontend**: http://localhost (ou votre domaine)
- **Backend API**: http://localhost:8000/docs
- **Streamlit** (optionnel): http://localhost:8501

---

## Option 2: Déploiement Manuel

### 2.1. Backend FastAPI

```bash
# Installer les dépendances
pip install -r backend/requirements.txt

# Configurer les variables d'environnement
export GROQ_API_KEY="votre_clé"
export GEMINI_API_KEY="votre_clé"

# Lancer avec Gunicorn (production)
cd backend
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2.2. Frontend React

```bash
cd frontend

# Installer les dépendances
npm install

# Build pour la production
npm run build

# Servir avec Nginx
sudo cp -r dist/* /var/www/html/
```

### 2.3. Configuration Nginx

```bash
sudo nano /etc/nginx/sites-available/findmyjobai
```

```nginx
server {
    listen 80;
    server_name findmyjobai.com www.findmyjobai.com;
    root /var/www/html;
    index index.html;

    # Proxy API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # React app
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/findmyjobai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Configuration des variables d'environnement

### Variables obligatoires

```env
# Clés API IA
GROQ_API_KEY=gsk_...                    # Groq (Llama 3.3) - GRATUIT
GEMINI_API_KEY=AIza...                  # Google Gemini - GRATUIT

# Frontend
VITE_API_URL=https://findmyjobai.com     # URL de votre backend
```

### Variables optionnelles (pour plus de sources d'emploi)

```env
# xAI (Grok)
XAI_API_KEY=xai-...

# France Travail (emplois en France)
FRANCE_TRAVAIL_CLIENT_ID=...
FRANCE_TRAVAIL_CLIENT_SECRET=...

# Autres sources
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
SERPAPI_KEY=...
JOOBLE_API_KEY=...
APIFY_API_KEY=...
```

---

## Nom de domaine et SSL

### Avec Let's Encrypt (GRATUIT)

```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir un certificat SSL
sudo certbot --nginx -d findmyjobai.com -d www.findmyjobai.com

# Renouvellement automatique
sudo certbot renew --dry-run
```

---

## Monitoring et maintenance

### Vérifier les logs

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Manuel
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Mettre à jour l'application

```bash
git pull origin main
docker-compose down
docker-compose up -d --build
```

### Sauvegardes

```bash
# Sauvegarder le .env
cp .env .env.backup

# Sauvegarder la base de données (si utilisée)
# (Actuellement pas de base de données, tout est en mémoire)
```

---

## 🎯 Checklist de déploiement

- [ ] Variables d'environnement configurées dans `.env`
- [ ] Clés API testées et fonctionnelles
- [ ] Nom de domaine pointé vers le serveur
- [ ] SSL/HTTPS configuré avec Let's Encrypt
- [ ] Firewall configuré (ports 80, 443 ouverts)
- [ ] Tests de charge effectués
- [ ] Monitoring en place (optionnel: Sentry, Datadog)
- [ ] Sauvegardes automatiques configurées

---

## 🆘 Support

- **GitHub Issues**: https://github.com/YaYouLeKyou/find-my-job-ai-react/issues
- **Email**: votre-email@example.com

---

## 📄 License

MIT