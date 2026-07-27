# France Travail API - Diagnostic et Solution

## Problème Identifié

L'API France Travail retourne **0 résultats** malgré le fait que les clés soient configurées.

### Cause Racine

Les **identifiants API (client_id et client_secret) sont invalides ou incorrects**.

Lors du test de l'authentification, l'API retourne :
```
HTTP 400 - {"error_description":"Client authentication failed","error":"invalid_client"}
```

Cela signifie que :
- ✅ Les clés sont présentes dans le fichier `.env`
- ❌ Les clés sont **rejetées par l'API France Travail** (invalides, expirées, ou mal configurées)

## Diagnostic Effectué

### 1. Vérification de la Configuration
```bash
✅ FRANCE_TRAVAIL_CLIENT_ID: PAR_jobbri... (configuré)
✅ FRANCE_TRAVAIL_CLIENT_SECRET: b7999c88... (configuré)
```

### 2. Test d'Authentification
```bash
🔑 Requesting France Travail access token...
   Client ID: PAR_jobbri...
   Auth URL: https://entreprise.pole-emploi.fr/connexion/oauth2/access_token
   Auth response status: 400
❌ France Travail auth failed: HTTP 400
   Response: {"error_description":"Client authentication failed","error":"invalid_client"}
```

### 3. Résultat
```
❌ No France Travail access token available
❌ France Travail: 0 résultat (source indisponible ou bloquée)
```

## Solution

### Étape 1 : Vérifier vos Identifiants France Travail

1. **Connectez-vous au portail Partenaires France Travail :**
   - URL: https://www.pole-emploi.fr/partenaires/devenir-partenaire
   - Ou: https://entreprise.pole-emploi.fr

2. **Vérifiez vos identifiants API :**
   - Client ID (clé publique)
   - Client Secret (clé secrète)

3. **Vérifiez que votre application est bien activée :**
   - L'application doit être en statut "Actif"
   - Les droits d'API doivent inclure `api_offresdemploiv2`

### Étape 2 : Mettre à Jour le Fichier `.env`

Remplacez les valeurs dans le fichier `.env` :

```env
# --- France Travail (Optionnel mais recommandé) ---
FRANCE_TRAVAIL_CLIENT_ID=votre_vrai_client_id_ici
FRANCE_TRAVAIL_CLIENT_SECRET=votre_vrai_client_secret_ici
```

**⚠️ Important :** 
- Ne partagez JAMAIS vos clés secrètes
- Les clés doivent être exactement celles fournies par France Travail
- Vérifiez qu'il n'y a pas d'espaces ou de caractères invisibles

### Étape 3 : Tester la Nouvelle Configuration

```bash
# Exécutez le script de test
python test_france_travail.py
```

Vous devriez voir :
```
✅ Access token obtained successfully
✅ France Travail: X results
```

## Améliorations Apportées au Code

### 1. **Meilleure Gestion de la Localisation**
- Avant: Si location="France", le paramètre `lieu` n'était pas envoyé
- Après: Le paramètre `lieu="France"` est toujours envoyé

### 2. **Authentification OAuth2 Corrigée**
- Ajout du paramètre `realm: "/partenaire"` requis par France Travail
- Timeout augmenté à 10s pour éviter les timeouts réseau

### 3. **Logging Détaillé**
- Logs de debug pour l'authentification
- Logs de debug pour les paramètres de recherche
- Messages d'erreur clairs en cas d'échec

### 4. **Gestion d'Erreur Améliorée**
- Détection spécifique des erreurs 400 (invalid_client)
- Messages guidant l'utilisateur vers le portail France Travail

## Vérification Post-Correction

Une fois les clés mises à jour, redémarrez le backend :

```bash
# Arrêtez le backend (Ctrl+C)
# Puis redémarrez
python main.py
# ou
uvicorn main:app --reload
```

Puis testez une recherche dans l'interface. Vous devriez maintenant voir :
```
✅ France Travail: X résultats
```

## Sources de Rechange (Fallback)

Si l'API France Travail ne fonctionne toujours pas, le système utilisera automatiquement :

1. **RSS Feed France Travail** (via enhanced_scrapers.py)
   - URL: https://candidat.francetravail.fr/emplois/recherche/rss
   - Pas besoin d'authentification
   - Limité mais fonctionnel

2. **Web Scraping** (via api.py)
   - Scraping du site web France Travail
   - Moins fiable mais fonctionne sans clé API

## Contact et Support

Si les problèmes persistent :
- Vérifiez le statut de votre application sur le portail Partenaires
- Contactez le support France Travail: https://www.pole-emploi.fr/contact
- Vérifiez les logs du backend pour plus de détails

## Fichiers Modifiés

- `backend/ai_modules/france_travail_api.py` - Client API avec améliorations
- `test_france_travail.py` - Script de test (nouveau)
- `FRANCE_TRAVAIL_FIX.md` - Cette documentation (nouveau)