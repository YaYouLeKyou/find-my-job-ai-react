# 🚀 Déploiement sur Netlify - FindMyJobAI

## 📋 Prérequis

- Compte Netlify (gratuit)
- Backend déployé (voir `DEPLOYMENT.md` pour les options)
- Repository GitHub connecté à Netlify

---

## 🎯 Étape 1: Déployer le Backend d'abord

Le frontend a besoin du backend pour fonctionner. Déployez d'abord le backend sur :

### Option A: Railway.app (Recommandé - Gratuit)
1. Allez sur [railway.app](https://railway.app)
2. Créez un nouveau projet
3. Connectez votre repo GitHub
4. Sélectionnez le dossier `backend`
5. Ajoutez les variables d'environnement :
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY`
   - `XAI_API_KEY` (optionnel)
   - `FRANCE_TRAVAIL_CLIENT_ID` (optionnel)
   - `FRANCE_TRAVAIL_CLIENT_SECRET` (optionnel)
   - `ADZUNA_APP_ID` (optionnel)
   - `ADZUNA_APP_KEY` (optionnel)
   - `SERPAPI_KEY` (optionnel)
   - `JOOBLE_API_KEY` (optionnel)
   - `APIFY_API_KEY` (optionnel)
6. Railway détectera automatiquement le `backend/Dockerfile`
7. Déployez et notez l'URL du backend (ex: `https://findmyjobai-backend.up.railway.app`)

### Option B: Render.com (Gratuit)
1. Allez sur [render.com](https://render.com)
2. Créez un "Web Service"
3. Connectez votre repo GitHub
4. Configuration :
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
5. Ajoutez les variables d'environnement
6. Déployez

### Option C: Fly.io (Gratuit)
```bash
# Installer Flyctl
curl -L https://fly.io/install.sh | sh

# Déployer
cd backend
flyctl launch
flyctl deploy
```

---

## 🎯 Étape 2: Déployer le Frontend sur Netlify

### Méthode 1: Via l'interface Netlify (Recommandé)

1. **Allez sur [app.netlify.com](https://app.netlify.com)**

2. **Créez un nouveau site**
   - Cliquez sur "Add new site" → "Import an existing project"
   - Choisissez GitHub comme provider
   - Sélectionnez votre repo `find-my-job-ai-react`

3. **Configurez le build**
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
   - **Node version**: `20`

4. **Ajoutez les variables d'environnement**
   - Allez dans "Site settings" → "Environment variables"
   - Ajoutez :
     ```
     VITE_API_URL=https://votre-backend-url.com
     ```
     (Remplacez par l'URL de votre backend déployé)

5. **Déployez**
   - Cliquez sur "Deploy site"
   - Attendez 2-3 minutes
   - Votre site sera accessible sur `https://votre-site.netlify.app`

### Méthode 2: Via Netlify CLI

```bash
# Installer Netlify CLI
npm install -g netlify-cli

# Se connecter
netlify login

# Déployer
cd frontend
netlify deploy --prod

# Ou pour un déploiement de preview
netlify deploy
```

---

## 🔧 Configuration du fichier `netlify.toml`

Le fichier `netlify.toml` à la racine est déjà configuré pour construire le frontend :

```toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"

# SPA fallback pour React Router
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

**Important** : définissez `VITE_API_URL` dans les variables d'environnement Netlify avec l'URL réelle de votre backend Railway. Le frontend utilise directement cette variable pour les appels API.

---

## 🌐 Configuration du nom de domaine (Optionnel)

### Avec un nom de domaine personnalisé

1. **Dans Netlify**
   - Allez dans "Site settings" → "Domain management"
   - Cliquez sur "Add custom domain"
   - Entrez votre domaine (ex: `findmyjobai.com`)

2. **Chez votre registrar** (OVH, Namecheap, etc.)
   - Ajoutez un enregistrement DNS :
     - **Type**: `CNAME`
     - **Name**: `www` (ou `@` pour le root)
     - **Value**: `votre-site.netlify.app`

3. **SSL automatique**
   - Netlify configure automatiquement Let's Encrypt
   - HTTPS est activé par défaut

---

## ✅ Vérification

### Testez votre application

1. **Frontend** : https://votre-site.netlify.app
2. **Backend** : https://votre-backend-url.com/docs
3. **Testez l'upload de CV**
4. **Testez la recherche d'emploi**

### Vérifiez les logs Netlify

```bash
# Via CLI
netlify logs

# Ou dans l'interface Netlify
# "Deploys" → Cliquez sur le déploiement → "Production log"
```

---

## 🔄 Mises à jour automatiques

Netlify redéploie automatiquement à chaque push sur `main` :

```bash
git push origin main
```

### Build hooks (Optionnel)

Pour déclencher un déploiement manuel :
1. "Site settings" → "Build & deploy" → "Build hooks"
2. Créez un hook
3. Utilisez l'URL dans vos CI/CD

---

## 🐛 Dépannage

### Erreur CORS

Si le frontend ne peut pas accéder au backend, vérifiez que le backend autorise votre domaine Netlify :

```python
# Dans backend/api.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://votre-site.netlify.app",
        "https://votre-site.netlify.app",
        "http://localhost:5173",  # Dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Erreur 404 sur les routes

Vérifiez que `netlify.toml` contient bien le fallback SPA :
```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### Variables d'environnement non trouvées

- Vérifiez que `VITE_API_URL` est bien définie dans Netlify
- Redéployez après avoir ajouté les variables

---

## 📊 Monitoring

### Netlify Analytics (Payant)
- Activez "Netlify Analytics" dans "Site settings"
- Statistiques de visiteurs

### Google Analytics (Gratuit)
Ajoutez dans `frontend/index.html` :
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
```

---

## 🎯 Checklist de déploiement Netlify

- [ ] Backend déployé et accessible
- [ ] `netlify.toml` configuré avec l'URL du backend
- [ ] Variables d'environnement ajoutées dans Netlify
- [ ] Build réussi sans erreur
- [ ] Site accessible via l'URL Netlify
- [ ] Upload de CV fonctionne
- [ ] Recherche d'emploi fonctionne
- [ ] Génération de lettre fonctionne
- [ ] SSL/HTTPS activé
- [ ] Nom de domaine personnalisé configuré (optionnel)

---

## 🆘 Support

- **Netlify Docs**: https://docs.netlify.com
- **Netlify Community**: https://community.netlify.com
- **GitHub Issues**: https://github.com/YaYouLeKyou/find-my-job-ai-react/issues

---

## 🎉 Félicitations !

Votre application FindMyJobAI est maintenant en ligne et accessible au monde entier ! 🚀

**URLs importantes** :
- Frontend: `https://votre-site.netlify.app`
- Backend: `https://votre-backend-url.com`
- API Docs: `https://votre-backend-url.com/docs`
