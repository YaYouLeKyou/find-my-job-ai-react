# 🔴 France Travail - Clés API Invalides

## Diagnostic Confirmé

Vos clés dans le `.env` :
```env
FRANCE_TRAVAIL_CLIENT_ID=PAR_jobbridge_f8038592684c898a2b92c2882b0e81de0c7939bfcd598294c88d15ca845a1d0e
FRANCE_TRAVAIL_CLIENT_SECRET=b7999c8838b6fd74e5f9f09a4153584e1ea9888f4d45a0a9c3b639779bb1bfde
```

**Résultat du test d'authentification :**
```
❌ HTTP 400 - invalid_client
{"error_description":"Client authentication failed","error":"invalid_client"}
```

---

## 🎯 Solution : Obtenir les Vraies Clés API

### Étape 1 : Accéder au Portail Partenaires France Travail

1. **Ouvrez votre navigateur** et allez à :
   ```
   https://www.pole-emploi.fr/partenaires/devenir-partenaire
   ```

2. **Connectez-vous** avec vos identifiants France Travail (Pôle Emploi)

### Étape 2 : Vérifier/Créer votre Application

1. **Accédez à votre tableau de bord développeur :**
   ```
   https://entreprise.pole-emploi.fr
   ```

2. **Vérifiez vos applications :**
   - Cherchez une application nommée "JobBridge" ou similaire
   - Vérifiez le statut : doit être **"Actif"** ou **"Validé"**

3. **Si l'application n'existe pas ou est inactive :**
   - Créez une nouvelle application
   - Remplissez le formulaire avec :
     - Nom de l'application : `JobBridge`
     - Description : `Application de recherche d'emploi intelligente`
     - URL de redirection : `http://localhost:8000/callback`
     - Scopes demandés : `api_offresdemploiv2`

### Étape 3 : Récupérer les Identifiants Corrects

1. **Dans le tableau de bord, sélectionnez votre application**

2. **Copiez les identifiants :**
   - **Client ID** (clé publique) : commence par `PAR_`
   - **Client Secret** (clé secrète) : chaîne hexadécimale de 64 caractères

3. **Vérifiez les droits d'accès :**
   - Assurez-vous que `api_offresdemploiv2` est bien activé
   - C'est le scope pour l'API des offres d'emploi v2

### Étape 4 : Mettre à Jour le Fichier `.env`

**AVANT (invalide) :**
```env
FRANCE_TRAVAIL_CLIENT_ID=PAR_jobbridge_f8038592684c898a2b92c2882b0e81de0c7939bfcd598294c88d15ca845a1d0e
FRANCE_TRAVAIL_CLIENT_SECRET=b7999c8838b6fd74e5f9f09a4153584e1ea9888f4d45a0a9c3b639779bb1bfde
```

**APRÈS (avec vos vraies clés) :**
```env
FRANCE_TRAVAIL_CLIENT_ID=PAR_votre_nouveau_client_id_ici
FRANCE_TRAVAIL_CLIENT_SECRET=votre_nouveau_client_secret_ici
```

### Étape 5 : Tester la Nouvelle Configuration

```bash
# Arrêtez le backend (Ctrl+C)
# Puis relancez le test
python test_france_travail.py
```

**Résultat attendu :**
```
✅ Access token obtained successfully
✅ France Travail: X résultats
```

---

## 🔍 Vérifications Importantes

### 1. Vérifier que l'Application est Active

Sur le portail Partenaires :
- [ ] L'application est en statut **"Actif"** (pas "En attente" ou "Rejeté")
- [ ] Les droits `api_offresdemploiv2` sont accordés
- [ ] Aucune action requise de votre part (pas de demande en cours)

### 2. Vérifier les Clés API

- [ ] Client ID commence bien par `PAR_`
- [ ] Client Secret fait 64 caractères hexadécimaux
- [ ] Pas d'espaces avant/après les clés dans `.env`
- [ ] Pas de guillemets autour des valeurs dans `.env`

### 3. Vérifier le Scope OAuth2

L'authentification demande le scope `api_offresdemploiv2` :
```python
{
    "grant_type": "client_credentials",
    "client_id": "VOTRE_CLIENT_ID",
    "client_secret": "VOTRE_CLIENT_SECRET",
    "scope": "api_offresdemploiv2",
    "realm": "/partenaire"
}
```

Assurez-vous que ce scope est bien activé dans votre application.

---

## 🚨 Erreurs Courantes

### Erreur 1 : "invalid_client"
**Cause :** Client ID ou Client Secret incorrect
**Solution :** Vérifiez vos identifiants sur le portail, régénérez le Client Secret si nécessaire

### Erreur 2 : "invalid_scope"
**Cause :** Le scope `api_offresdemploiv2` n'est pas activé
**Solution :** Activez le scope dans les paramètres de votre application

### Erreur 3 : "invalid_grant"
**Cause :** Problème avec grant_type ou realm
**Solution :** Vérifiez que `grant_type=client_credentials` et `realm=/partenaire` sont corrects

### Erreur 4 : HTTP 401
**Cause :** Token expiré ou invalide
**Solution :** Le système régénère automatiquement le token, vérifiez vos clés

---

## 📞 Support France Travail

Si vous ne pouvez pas accéder au portail ou si vos clés restent invalides :

1. **Contactez le support développeur :**
   - Email: partenaires@pole-emploi.fr
   - Téléphone: 39 95 (service gratuit + prix d'un appel)

2. **Vérifiez le statut des API :**
   - Status: https://www.pole-emploi.fr/etat-services
   - Documentation: https://www.pole-emploi.fr/partenaires/devenir-partenaire

3. **Consultez la documentation technique :**
   - Swagger: https://api.pole-emploi.io/partenaire/offresdemploi/v2/swagger-ui.html
   - Guide OAuth2: https://www.pole-emploi.fr/partenaires/devenir-partenaire/authentification

---

## ✅ Solution Temporaire (en attendant)

Si vous ne pouvez pas corriger les clés immédiatement, le système utilisera automatiquement :

1. **RSS Feed France Travail** (sans authentification)
   - URL: https://candidat.francetravail.fr/emplois/recherche/rss
   - Limité mais fonctionnel
   - Pas de clé API requise

2. **Web Scraping** (fallback)
   - Scraping du site web France Travail
   - Moins fiable mais fonctionne sans clé

Ces solutions sont déjà implémentées dans le code et s'activent automatiquement quand l'API officielle échoue.

---

## 🎓 Pour Résumer

**Le problème n'est PAS dans le code** - le code est correct.

**Le problème EST dans les clés API** - elles sont invalides ou l'application n'est pas activée.

**Action requise :**
1. Allez sur https://www.pole-emploi.fr/partenaires/devenir-partenaire
2. Vérifiez/récupérez vos vraies clés API
3. Mettez à jour le fichier `.env`
4. Testez avec `python test_france_travail.py`

Une fois les clés corrigées, France Travail fonctionnera et vous obtiendrez des résultats supplémentaires.