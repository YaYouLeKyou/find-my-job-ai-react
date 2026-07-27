# 🎯 Récupérer les Clés API France Travail

## ✅ Confirmation
- **Application :** Job Bridge ✅
- **API autorisée :** Offres d'emploi v2 (10 appels/seconde) ✅
- **Problème :** Les clés dans `.env` sont invalides ❌

---

## 📋 Procédure pour Récupérer les Clés

### 1. Accéder au Tableau de Bord

**URL :** https://entreprise.pole-emploi.fr

1. Connectez-vous avec vos identifiants
2. Cliquez sur **"Mes applications"** ou **"Mes API"**
3. Sélectionnez **"Job Bridge"**

### 2. Récupérer le Client ID

**Le Client ID est visible :**
```
PAR_jobbridge_f8038592684c898a2b92c2882b0e81de0c7939bfcd598294c88d15ca845a1d0e
```

**Vérifiez que c'est bien celui-ci** (commence par `PAR_`)

### 3. Récupérer le Client Secret

**Le Client Secret est MASQUÉ** pour la sécurité.

**Pour le voir :**
1. Cherchez le bouton **"👁️ Afficher"** ou **"📋 Copier"** à côté du Client Secret
2. OU cherchez **"🔄 Régénérer le secret"** si vous ne l'avez jamais copié

**⚠️ Important :**
- Si vous régénérez le secret, l'ancien ne fonctionnera plus
- Copiez-le immédiatement (affiché une seule fois)

**Format attendu :**
```
b7999c8838b6fd74e5f9f09a4153584e1ea9888f4d45a0a9c3b639779bb1bfde
```
(64 caractères hexadécimaux)

### 4. Vérifier les Scopes

Dans la page de l'application, vérifiez :

```
✅ Scopes autorisés :
   - api_offresdemploiv2
```

**Si le scope n'est pas là :**
1. Cliquez sur **"Modifier les scopes"**
2. Ajoutez `api_offresdemploiv2`
3. Sauvegardez

---

## 🔧 Mettre à Jour le Fichier `.env`

### Éditez le fichier `.env` :

```env
# France Travail API
FRANCE_TRAVAIL_CLIENT_ID=PAR_jobbridge_f8038592684c898a2b92c2882b0e81de0c7939bfcd598294c88d15ca845a1d0e
FRANCE_TRAVAIL_CLIENT_SECRET=[VOTRE_VRAI_SECRET_ICI]
```

**Remplacez `[VOTRE_VRAI_SECRET_ICI]` par le vrai secret que vous avez copié.**

---

## 🧪 Tester la Configuration

### Méthode 1 : Script de Test

```bash
# Arrêtez le backend (Ctrl+C)
# Puis lancez :
python test_france_travail.py
```

**Résultat attendu :**
```
✅ Access token obtained successfully
✅ France Travail: X résultats
```

### Méthode 2 : Via l'Interface

1. **Redémarrez le backend** après avoir modifié `.env`
2. **Lancez une recherche** avec France Travail coché
3. **Vérifiez les logs** :
   ```
   ✅ France Travail: X résultats
   ```

---

## 🚨 Si Ça Ne Fonctionne Toujours Pas

### Vérifications :

1. **Pas d'espaces dans `.env` :**
   ```env
   # ❌ MAUVAIS
   FRANCE_TRAVAIL_CLIENT_SECRET= b7999c88...
   
   # ✅ BON
   FRANCE_TRAVAIL_CLIENT_SECRET=b7999c88...
   ```

2. **Pas de guillemets :**
   ```env
   # ❌ MAUVAIS
   FRANCE_TRAVAIL_CLIENT_SECRET="b7999c88..."
   
   # ✅ BON
   FRANCE_TRAVAIL_CLIENT_SECRET=b7999c88...
   ```

3. **Redémarrez le backend** après chaque modification de `.env`

4. **Vérifiez les logs** pour voir l'erreur exacte

---

## 📞 Support

Si vous ne trouvez pas le Client Secret :

1. **Sur le portail**, cherchez :
   - Section **"Sécurité"** ou **"Clés API"**
   - Bouton **"Afficher les secrets"**
   - Bouton **"Régénérer le Client Secret"**

2. **Contactez le support :**
   - Email: partenaires@pole-emploi.fr
   - Documentation: https://www.pole-emploi.fr/partenaires/devenir-partenaire

---

## ✅ Résumé

**Action à faire maintenant :**
1. Allez sur https://entreprise.pole-emploi.fr
2. Ouvrez votre application "Job Bridge"
3. Copiez le Client Secret (ou régénérez-le)
4. Mettez à jour `.env`
5. Testez avec `python test_france_travail.py`

**Une fois fait, France Travail fonctionnera et vous aurez +10-15 offres supplémentaires.**