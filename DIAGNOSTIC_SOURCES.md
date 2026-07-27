# Diagnostic Détaillé des Sources d'Emploi

## Résumé du Problème

**Seulement 9 offres obtenues sur 18 sources actives**, malgré des clés API configurées.

### Logs du Backend (Analyse)

```
✅ LinkedIn: 10 jobs in 1.31s
❌ Indeed: 0 results in 0.42s
❌ France Travail: 0 results (INVALID CREDENTIALS)
❌ Google Jobs: 0 results (SerpApi timeout)
❌ Adzuna: 0 résultats bruts (HTTP 200 mais vide)
❌ Jooble: 0 results (HTTP 403 Forbidden)
🛡️ Glassdoor: bloqué par Cloudflare
🛡️ ZipRecruiter: bloqué par Cloudflare
❌ Simplyhired: 0 results (scraper bloqué)
⚠️ Careerbuilder: indisponible
⚠️ Monster: indisponible
❌ Reed: 0 results
❌ StepStone: 0 results
❌ Xing: 0 results
❌ Dice: 0 results
❌ Seek: 0 results
❌ RégionsJob: 0 results
❌ LesJeudis: 0 results
❌ Talent.io: 0 results
```

---

## Analyse Source par Source

### 1. 🔴 France Travail - **CREDENTIALS INVALIDES**

**Problème :**
```
HTTP 400 - {"error_description":"Client authentication failed","error":"invalid_client"}
```

**Cause :** Les clés API dans `.env` sont rejetées par l'authentification OAuth2.

**Solutions :**
1. **Vérifier vos identifiants sur le portail Partenaires :**
   - URL: https://www.pole-emploi.fr/partenaires/devenir-partenaire
   - Connectez-vous et vérifiez votre Client ID et Client Secret

2. **Vérifier le statut de votre application :**
   - L'application doit être en statut "Actif"
   - Les droits doivent inclure `api_offresdemploiv2`

3. **Régénérer les clés si nécessaire :**
   - Sur le portail, régénérez votre Client Secret
   - Mettez à jour le fichier `.env`

4. **Solution temporaire (sans clé API) :**
   - Le système utilise automatiquement le RSS Feed France Travail
   - URL: https://candidat.francetravail.fr/emplois/recherche/rss
   - Limité mais fonctionnel

**Fichier de test :** `test_france_travail.py`

---

### 2. 🔴 Indeed - **SCRAPER BLOQUÉ**

**Problème :**
```
Indeed: 0 results in 0.42s
```

**Cause :** Indeed bloque les scrapers automatisés avec :
- Détection de bot (User-Agent, comportement)
- Rate limiting agressif
- CAPTCHA

**Solutions :**

1. **Utiliser JobSpy (recommandé) :**
   ```python
   # Dans App.jsx, sélectionnez "Indeed" dans les sources
   # Le système utilisera automatiquement JobSpy
   ```
   - JobSpy utilise des techniques anti-détection
   - Plus fiable que le scraping direct

2. **Activer Playwright pour Indeed :**
   ```python
   # Dans backend/ai_modules/playwright_scraper.py
   # Indeed est déjà configuré pour Playwright
   ```
   - Playwright contourne les protections JavaScript
   - Plus lent mais plus fiable

3. **Solutions alternatives :**
   - Utiliser l'API Indeed Publisher (gratuite avec inscription)
   - Utiliser RSS Feed Indeed: https://fr.indeed.com/rss

---

### 3. 🔴 Google Jobs (SerpApi) - **TIMEOUT**

**Problème :**
```
SerpApi error: HTTPSConnectionPool(host='serpapi.com', port=443): Read timed out. (read timeout=5)
```

**Cause :** 
- Timeout de 5 secondes trop court pour SerpApi
- SerpApi peut être lent selon la charge
- Problème réseau possible

**Solutions :**

1. **Augmenter le timeout :**
   ```python
   # Dans backend/api.py, ligne ~668
   response = requests.get(url, params=params, timeout=15)  # Au lieu de 5
   ```

2. **Vérifier votre clé SerpApi :**
   - URL: https://serpapi.com/
   - Vérifiez le quota de requêtes
   - Vérifiez que la clé est valide

3. **Solution de contournement :**
   - Désactiver Google Jobs si SerpApi n'est pas fiable
   - Utiliser d'autres sources (LinkedIn, Adzuna)

---

### 4. 🟡 Adzuna - **QUOTA DÉPASSÉ OU PAS DE RÉSULTATS**

**Problème :**
```
Adzuna: HTTP 200
Adzuna: 0 résultats bruts
```

**Cause :** 
- HTTP 200 = authentification OK
- 0 résultats = soit quota dépassé, soit pas d'offres pour cette recherche

**Solutions :**

1. **Vérifier votre quota Adzuna :**
   - URL: https://developer.adzuna.com/
   - Vérifiez le nombre de requêtes restantes
   - Plan gratuit: 1000 requêtes/mois

2. **Tester avec une recherche plus large :**
   - Essayez "Développeur" au lieu de "Développeur Web Front-end"
   - Essayez "Paris" au lieu de "Bondy, France"

3. **Vérifier les paramètres de recherche :**
   ```python
   # Dans backend/api.py, ligne ~617
   params = {
       "app_id": adzuna_app_id,
       "app_key": adzuna_app_key,
       "results_per_page": limit,
       "what": job_title,
       "where": location,
       "content-type": "application/json"
   }
   ```

---

### 5. 🔴 Jooble - **HTTP 403 FORBIDDEN**

**Problème :**
```
Jooble: HTTP 403
<!DOCTYPE html><html>...<title>Error 403</title>...
```

**Cause :** Jooble bloque les requêtes API automatisées.

**Solutions :**

1. **Vérifier votre clé Jooble :**
   - URL: https://jooble.org/api
   - Vérifiez que la clé est valide et active

2. **Utiliser le scraping web (fallback) :**
   ```python
   # Le système a déjà un scraper HTML pour Jooble
   # Mais il est aussi bloqué par le WAF
   ```

3. **Solutions alternatives :**
   - Jooble est très restrictif
   - Privilégiez d'autres sources (LinkedIn, Indeed via JobSpy)

---

### 6. 🛡️ Glassdoor & ZipRecruiter - **CLOUDFLARE/WAF**

**Problème :**
```
Glassdoor: bloqué par Cloudflare/WAF
ZipRecruiter: bloqué par Cloudflare/WAF
```

**Cause :** Ces sites utilisent Cloudflare pour bloquer les scrapers.

**Solutions :**

1. **Activer Playwright (déjà fait) :**
   ```python
   # Playwright contourne Cloudflare
   # Mais nécessite plus de temps de chargement
   ```

2. **Utiliser JobSpy :**
   ```python
   # JobSpy inclut Glassdoor et ZipRecruiter
   # Mais nécessite des clés API valides
   ```

3. **Solutions alternatives :**
   - Ces sources sont difficiles à scraper
   - Concentrez-vous sur LinkedIn, Indeed, France Travail

---

### 7. ⚠️ Sources Indisponibles - **SITES HORS SERVICE OU BLOQUÉS**

**Sources concernées :**
- Careerbuilder, Monster, Reed, StepStone, Xing, Dice, Seek, RégionsJob, LesJeudis, Talent.io

**Causes possibles :**
- Sites fermés ou fusionnés
- Changements de structure HTML
- Blocage géographique

**Solutions :**

1. **Vérifier manuellement les sites :**
   - Ouvrez les URLs dans un navigateur
   - Vérifiez si les sites sont toujours actifs

2. **Mettre à jour les sélecteurs :**
   ```python
   # Dans backend/ai_modules/enhanced_scrapers.py
   # Les sélecteurs CSS peuvent être obsolètes
   ```

3. **Supprimer les sources mortes :**
   - Retirez-les de la liste des sources dans le frontend
   - Cela accélère les recherches

---

## Solutions Globales

### 1. ✅ Sources qui Fonctionnent

**LinkedIn (9 résultats) :**
- ✅ Fonctionne parfaitement
- ✅ Pas de clé API requise
- ✅ Résultats de qualité

**Pourquoi LinkedIn fonctionne :**
- Moins de protection anti-bot
- Structure HTML stable
- User-Agent rotation efficace

### 2. 🔧 Actions Prioritaires

**Action 1 : Corriger France Travail**
```bash
# 1. Récupérez vos vraies clés sur:
https://www.pole-emploi.fr/partenaires/devenir-partenaire

# 2. Mettez à jour .env
FRANCE_TRAVAIL_CLIENT_ID=votre_vrai_client_id
FRANCE_TRAVAIL_CLIENT_SECRET=votre_vrai_client_secret

# 3. Testez
python test_france_travail.py
```

**Action 2 : Activer JobSpy pour Indeed**
```javascript
// Dans frontend/src/App.jsx
// Cochez "Indeed" dans les sources
// Le système utilisera automatiquement JobSpy
```

**Action 3 : Augmenter les timeouts**
```python
# Dans backend/api.py
# Augmentez les timeouts de 5s à 10-15s
timeout=15  # Au lieu de timeout=5
```

**Action 4 : Désactiver les sources mortes**
```python
# Dans frontend/src/App.jsx
# Supprimez les sources qui ne fonctionnent jamais:
- Careerbuilder
- Monster
- Reed
- StepStone
- Xing
- Dice
- Seek
- RégionsJob
- LesJeudis
- Talent.io
```

### 3. 📊 Configuration Optimale

**Sources recommandées (par ordre de fiabilité) :**

1. ✅ **LinkedIn** - Fonctionne toujours
2. ✅ **France Travail** - Après correction des clés
3. ✅ **Indeed (via JobSpy)** - Plus fiable que le scraping direct
4. ✅ **Adzuna** - Vérifier le quota
5. ✅ **Google Jobs (SerpApi)** - Après augmentation du timeout
6. ⚠️ **Glassdoor/ZipRecruiter** - Via Playwright seulement
7. ❌ **Jooble** - Très restrictif, à éviter
8. ❌ **Sources mortes** - À supprimer

**Configuration suggérée :**
```javascript
const RECOMMENDED_SOURCES = [
  'LinkedIn',
  'France Travail',
  'Indeed',
  'Adzuna',
  'Google Jobs',
  'Glassdoor',  // Via Playwright
  'ZipRecruiter',  // Via Playwright
  'Welcome to the Jungle',
  'HelloWork',
  'APEC'
];
```

### 4. 🚀 Améliorations Futures

**Court terme (1-2 jours) :**
1. Corriger les credentials France Travail
2. Augmenter les timeouts API
3. Désactiver les sources mortes

**Moyen terme (1 semaine) :**
1. Implémenter un système de cache Redis (déjà fait, mais timeout de connexion)
2. Ajouter plus de sources françaises (APEC, HelloWork, WTTJ)
3. Améliorer la détection de blocage

**Long terme (1 mois) :**
1. Utiliser des proxies rotatifs pour éviter les blocages
2. Implémenter un système de queue pour les requêtes
3. Ajouter des sources internationales (Allemagne, UK, etc.)

---

## Vérification Post-Correction

Après avoir appliqué les corrections :

1. **Redémarrez le backend :**
   ```bash
   # Arrêtez (Ctrl+C) puis redémarrez
   .\start_backend.bat
   ```

2. **Vérifiez les logs :**
   ```
   ✅ France Travail: X résultats
   ✅ Indeed: X résultats (via JobSpy)
   ✅ Google Jobs: X résultats
   ```

3. **Testez une recherche :**
   - Recherchez "Développeur Web Front-end"
   - Vous devriez voir au moins 20-30 offres

---

## Support

Si les problèmes persistent :
1. Vérifiez les logs du backend pour les erreurs détaillées
2. Testez chaque source individuellement avec `test_france_travail.py`
3. Vérifiez vos clés API sur les portails respectifs
4. Consultez la documentation de chaque API

**Fichiers modifiés :**
- `backend/ai_modules/france_travail_api.py` - Meilleure gestion d'erreur
- `test_france_travail.py` - Script de test
- `FRANCE_TRAVAIL_FIX.md` - Documentation France Travail
- `DIAGNOSTIC_SOURCES.md` - Ce fichier