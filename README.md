# 🤖 Gestionnaire Bot — Guide complet

Bot Telegram de gestion financière pour commerçants et particuliers (Afrique de l'Ouest).

---

## 📋 Prérequis

- Python 3.11
- Compte Telegram
- Compte Supabase (gratuit) → https://supabase.com
- Clé API Gemini (gratuit) → https://aistudio.google.com
- Compte GitHub → https://github.com
- Compte Render (gratuit) → https://render.com

---

## 🚀 Installation locale (pour développer)

### 1. Créer le bot Telegram
- Cherche @BotFather sur Telegram
- Envoie /newbot et suis les instructions
- Copie le token reçu

### 2. Configurer Supabase
- Crée un projet sur supabase.com
- Va dans SQL Editor et exécute supabase_tables.sql
- Copie l'URL et la clé anon dans Settings > API

### 3. Obtenir la clé Gemini
- Va sur aistudio.google.com
- Clique sur "Get API Key"

### 4. Configurer le .env
```
cp .env.example .env
```
Remplis les 4 clés dans le fichier .env

### 5. Lancer le bot
```
pip install -r requirements.txt
python main.py
```

---

## 🌐 Déploiement sur Render (bot 24h/24)

### 1. Mettre le code sur GitHub
- Crée un repo sur github.com
- Upload tous les fichiers (sauf .env)

### 2. Créer le service sur Render
- Va sur render.com > New > Background Worker
- Connecte ton repo GitHub
- Build Command : pip install -r requirements.txt
- Start Command : python main.py

### 3. Ajouter les variables d'environnement
Dans Render > Environment, ajoute tes 4 clés :
- TELEGRAM_TOKEN
- SUPABASE_URL
- SUPABASE_KEY
- GEMINI_API_KEY

### 4. Déployer
Clique Deploy — ton bot tourne maintenant 24h/24 !

---

## 💬 Utilisation

### Mode Particulier 👤
| Action | Comment |
|--------|---------|
| Enregistrer une dépense | repas 1500 ou transport 500 taxi |
| Bilan du jour | Bouton 📊 ou /bilan |
| Bilan semaine + IA | Bouton 📅 ou /semaine |
| Budget optimal | Bouton 💰 ou /budget |
| Historique par mois | Bouton 📅 Historique |
| Objectifs & alertes | Bouton 🎯 ou /newobjectif |
| Changer de profil | Bouton 🔄 ou /profil |

### Mode Commerçant 🏪
| Action | Comment |
|--------|---------|
| Enregistrer une vente | vendu pagne 3 5000 |
| Bilan du jour | Bouton 📊 ou /bilan |
| Bilan semaine + stratégies | Bouton 📅 ou /semaine |
| Gérer les stocks | Bouton 📦 ou /stock |
| Clients et dettes | Bouton 👥 ou /clients |
| Marges bénéficiaires | Bouton 📊 Mes marges |
| Top produits | Bouton 📈 ou /topproduits |

---

## 📁 Structure du projet
```
gestionnaire-bot/
├── main.py                    # Point d'entrée
├── requirements.txt
├── render.yaml                # Config déploiement Render
├── supabase_tables.sql        # Script SQL Supabase
├── .env                       # Clés API (ne jamais partager)
├── .gitignore
├── handlers/
│   ├── onboarding.py          # Inscription et menus
│   ├── depenses.py            # Module particulier
│   ├── stocks.py              # Module commerçant
│   ├── clients.py             # Clients et dettes
│   ├── marges.py              # Marges et historique produits
│   ├── objectifs.py           # Objectifs d'épargne
│   └── historique.py          # Historique et export
└── services/
    ├── database.py            # Requêtes Supabase
    ├── claude_ai.py           # Analyses Gemini
    ├── scheduler.py           # Rapports automatiques
    └── erreurs.py             # Gestionnaire d'erreurs
```
