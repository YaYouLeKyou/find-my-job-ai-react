# 🚀 Démarrage de FindMyJobAI en Mode Test

Guide pour lancer l'application en local pour les tests.

## 📋 Prérequis

- Python 3.11+ installé
- Node.js 20+ installé
- Les clés API dans le fichier `.env`

## 🎯 Démarrage Rapide

### Option 1 : Application Complète (Backend + Frontend)

#### Terminal 1 - Backend :
```bash
cd backend
python -m uvicorn api:app --reload --port 8000
```

#### Terminal 2 - Frontend :
```bash
cd frontend
npm install
npm run dev
```

**Accédez à l'application** : http://localhost:5173

---

### Option 2 : Version Streamlit (Tout-en-un)

```bash
python -m streamlit run main.py
```

**Accédez à l'application** : http://localhost:8501

---

## 🔧 Configuration des Variables d'Environnement

### 1. Copier le fichier d'exemple
```bash
cp .env.example .env
```

### 2. Éditer le fichier `.env` avec vos clés API

```env
# Obligatoire
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...

# Optionnel mais recommandé
XAI_API_KEY=xai-...
FRANCE_TRAVAIL_CLIENT_ID=...
FRANCE_TRAVAIL_CLIENT_SECRET=...
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
SERPAPI_KEY=...
JOOBLE_API_KEY=...
APIFY_API_KEY=...

# Frontend
VITE_API_URL=http://localhost:8000

# Redis (optionnel)
REDIS_URL=localhost:6379

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 🧪 Tests à Effectuer

### 1. Upload de CV
- [ ] Glisser-déposer un fichier PDF
- [ ] Vérifier l'extraction du texte
- [ ] Vérifier l'analyse IA (métier, compétences, etc.)

### 2. Recherche d'emploi
- [ ] Lancer une recherche avec le métier détecté
- [ ] Vérifier les résultats sur plusieurs sources
- [ ] Tester les filtres (contrat, remote, localisation)
- [ ] Vérifier le classement IA

### 3. Fonctionnalités
- [ ] Historique des recherches (onglet 📋)
- [ ] Favoris (bouton étoile ⭐)
- [ ] Export CSV
- [ ] Mode sombre/clair (bouton 🌓)
- [ ] Copier lettre de motivation
- [ ] Pagination des résultats

### 4. Performance
- [ ] Vérifier le temps de recherche affiché
- [ ] Tester le cache (2ème recherche identique = plus rapide)
- [ ] Vérifier les notifications toast

---

## 🐛 Dépannage

### Backend ne démarre pas
```bash
# Vérifier les dépendances
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Vérifier les variables d'environnement
cat .env
```

### Frontend ne démarre pas
```bash
# Réinstaller les dépendances
cd frontend
rm -rf node_modules package-lock.json
npm install

# Vérifier la variable VITE_API_URL
cat .env
```

### Erreur CORS
- Vérifiez que `ALLOWED_ORIGINS` contient `http://localhost:5173`
- Redémarrez le backend après modification

### Redis non disponible
- Installez Redis : https://redis.io/docs/getting-started/installation/
- Ou lancez avec Docker : `docker run -d -p 6379:6379 redis:alpine`
- Le cache est optionnel, l'app fonctionne sans

---

## 📊 Vérification

### Backend Health Check
```bash
curl http://localhost:8000/api/health
```

Réponse attendue :
```json
{
  "status": "healthy",
  "ollama_online": false
}
```

### Frontend
Ouvrez http://localhost:5173 dans votre navigateur

---

## 🎯 Tests d'Intégration

### Test 1 : Analyse de CV
1. Uploadez un CV PDF
2. Vérifiez que l'analyse retourne :
   - Nom complet
   - Métier
   - Compétences
   - Expérience
   - Recommandations

### Test 2 : Recherche d'emploi
1. Utilisez le métier détecté
2. Lancez la recherche
3. Vérifiez :
   - Résultats affichés
   - Sources multiples
   - Scores de pertinence
   - Temps de recherche

### Test 3 : Lettre de motivation
1. Cliquez sur "Lettre de Motivation" sur une offre
2. Générez la lettre
3. Copiez-la
4. Téléchargez-la

---

## 🚀 Prêt pour la Production ?

Une fois tous les tests passés :

1. **Déployez sur Railway** (voir `DEPLOYMENT_RAILWAY.md`)
2. **Configurez les variables d'environnement** de production
3. **Testez la version en ligne**
4. **Partagez le lien** avec vos utilisateurs

---

## 📝 Notes

- **Mode debug** : Les logs sont activés pour le debugging
- **Performance** : Le cache Redis accélère les recherches répétées
- **Sécurité** : CORS restrictif en production, ouvert en dev
- **Données** : Historique et favoris stockés dans localStorage

Bon test ! 🎉