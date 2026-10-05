# Instructions Copilot : financial-sec-pipeline

## Contexte et objectif

Ce dépôt est un projet étudiant de Data Engineering et de cybersécurité. Il récupère des données de marché Yahoo Finance, les transforme, les stocke dans PostgreSQL et les présente avec Streamlit. L'objectif de Mehdi est de comprendre l'architecture et les choix de cybersécurité pour pouvoir les expliquer en entretien, pas de mémoriser chaque ligne de code.

Répondre en français, de façon concise et progressive. Pour toute brique liée à la sécurité, expliquer brièvement : ce qu'elle fait, la menace visée et la défense appliquée. Le code secondaire (graphiques, présentation, plomberie) peut être fourni directement avec une courte explication.

## Façon de modifier le dépôt

- Lire les fichiers concernés avant de proposer ou d'effectuer une modification. Faire des changements ciblés et préserver le style existant ; ne jamais réécrire un fichier entier sans nécessité.
- S'appuyer sur le code présent plutôt que sur un ancien résumé : vérifier l'état des fonctionnalités, des branches et des PR avant de les décrire comme actuels.
- Ne pas modifier des fichiers hors du périmètre demandé. Préserver les changements préexistants de l'utilisateur.
- Utiliser 4 espaces en Python, sans tabulations. Préférer les noms explicites et les commentaires seulement lorsqu'ils clarifient une logique non évidente.
- Après une modification, lancer le contrôle le plus ciblé disponible. Pour la suite de tests du dépôt, utiliser `python -m pytest tests/` afin d'éviter que pytest explore `postgres_data/`.
- Ne jamais afficher ou demander le contenu des secrets. Pour diagnostiquer les noms des variables d'un `.env`, utiliser `cut -d= -f1 .env`.

## Architecture

Flux attendu : Yahoo Finance (`yfinance`) -> `etl/extract.py` -> `etl/transform.py` -> `etl/load.py` -> PostgreSQL -> `app/dashboard.py` (Streamlit). Docker Compose fournit l'infrastructure locale. Les actifs suivis sont `AAPL`, `MSFT` et `BTC-USD`.

- `etl/extract.py` : acquisition des données ; vérifier les données externes comme non fiables.
- `etl/transform.py` : nettoyage, validation et calcul des indicateurs.
- `etl/load.py` : persistance idempotente et journalisation dans `audit_logs`.
- `sql/init/01_init.sql` : schéma de base, notamment `assets`, `asset_prices`, `indicators` et `audit_logs`.
- `sql/init/02_security.sql` et `sql/init/03_application_roles.sh` : schéma d'authentification et rôles PostgreSQL pour le dashboard et l'ETL.
- `app/dashboard.py` : consultation Streamlit des données de marché, indicateurs et journaux d'audit.
- `security/auth.py` et `security/database.py` : authentification bcrypt, limitation des tentatives, rôles et connexion SQLAlchemy.
- `dags/market_pipeline.py` : DAG quotidien `extract -> transform -> load`.
- `tests/test_transform.py` : tests des transformations.
- `tests/test_auth.py` : tests de hachage de mots de passe et de configuration SQL.

Vérifier les migrations et les privilèges sur une base réelle avant d'affirmer que l'authentification, le RBAC ou le déploiement sont validés de bout en bout.

## Environnement et commandes

Le développement se fait sous Linux/Debian avec Python 3.9+ dans un environnement virtuel. Les paramètres PostgreSQL utilisent le préfixe `POSTGRES_` : `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`. Les secrets locaux vont dans `.env`, jamais dans Git ; `.env.example` ne contient que des valeurs d'exemple.

Commandes locales courantes :

```sh
source venv/bin/activate
docker compose up -d
python -m pytest tests/
streamlit run app/dashboard.py
```

Ouvrir manuellement `http://localhost:8501` si l'ouverture automatique du navigateur échoue ; le message `gio: ... Operation not supported` est sans gravité.

## Sécurité : règles à appliquer

- Construire les connexions SQLAlchemy avec `sqlalchemy.engine.URL.create(...)`, pas par concaténation ou f-string : les caractères réservés d'un mot de passe peuvent casser une URL. Si `POSTGRES_PASSWORD` manque, arrêter clairement l'application au démarrage au lieu de masquer l'erreur par une valeur par défaut vide.
- Toute valeur provenant d'un utilisateur doit passer par des requêtes paramétrées, par exemple `text("... :param ...")` et `params={...}`. Ne jamais interpoler une valeur dans du SQL par f-string.
- Si l'authentification est implémentée, stocker uniquement des empreintes de mots de passe avec sel via bcrypt ou Argon2, jamais les mots de passe en clair. Prévoir une limitation des tentatives et un verrouillage temporaire.
- Si le RBAC est implémenté, appliquer les contrôles côté serveur : Analyste pour le marché et les indicateurs ; Auditeur pour ces vues et les journaux d'audit, dont la colonne `details`. Ne pas considérer le masquage d'un onglet comme un contrôle d'accès.
- Ne pas mettre en cache partagé avec `st.cache_data` des données qui dépendent de l'identité ou du rôle. En particulier, protéger les journaux d'audit contre toute fuite entre utilisateurs.
- Garder PostgreSQL sur le réseau Docker sans publier le port 5432 sur toutes les interfaces. Utiliser un compte applicatif aux privilèges minimaux ; préférer un compte en lecture seule pour le dashboard.
- Traiter les entrées de marché comme non fiables : valider prix, cohérence OHLC, volume, symbole et date ; rejeter les lignes invalides et tracer les rejets sans exposer de secrets ni de détails internes sensibles.
- Pour les secrets, respecter `.gitignore`. Ne jamais utiliser `git add .` ; vérifier `git status` puis ajouter uniquement les fichiers voulus. Examiner toute baseline `detect-secrets` avant de la commiter et vérifier qu'aucune entrée ne révèle `.env` ou un secret.

## État du code observé

Ces constats sont un instantané et doivent être revérifiés avant d'en faire des affirmations :

- `etl/transform.py` contient `clean_data`, `validate_data` et `compute_indicators`. La validation actuelle couvre les quatre prix strictement positifs, la cohérence OHLC, un volume positif ou nul, les dates non futures et les symboles autorisés.
- `daily_return` est calculé avec `pct_change() * 100` : il est exprimé en pourcentage. `volatility` est l'écart-type glissant sur cinq valeurs de ces rendements ; sa valeur est donc aussi exprimée en points de pourcentage. `moving_avg` est une moyenne glissante sur cinq cours de clôture.
- `app/dashboard.py` emploie `text()` et des paramètres, et délègue sa connexion à `security/database.py` qui utilise `URL.create(...)`. L'audit n'est pas mis en cache ; `load_audit_logs` vérifie le rôle Auditeur côté serveur.
- L'authentification stocke les empreintes bcrypt, verrouille un identifiant après cinq échecs pendant quinze minutes, et enregistre les événements de connexion dans `audit_logs`.
- `docker-compose.yml` ne publie pas le port PostgreSQL. Le rôle dashboard est en lecture seule sur les données de marché ; le rôle ETL dispose des droits nécessaires à ses UPSERT et aux logs.
- Airflow utilise actuellement `SequentialExecutor` et une base SQLite locale temporaire : configuration pédagogique uniquement, à remplacer pour un déploiement durable ou en production.
- Vérifier les onglets du dashboard et les actifs individuellement avant de dire qu'ils ont tous été testés. Pour BTC-USD, vérifier notamment la continuité des dates de week-end.

## Priorités connues

Confirmer d'abord les faits dans le dépôt et Git, puis traiter les tâches encore manquantes dans cet ordre adapté au périmètre :

1. Ajouter les variables `DASHBOARD_DB_*` et `ETL_DB_*` à `.env` sans afficher ni versionner les secrets, appliquer les migrations à toute base déjà initialisée, puis créer les utilisateurs Analyste et Auditeur.
2. Tester les rôles, le verrouillage, les logs d'audit et les privilèges PostgreSQL sur une base de test réelle ; tester le dashboard et le DAG en exécution de bout en bout.
3. Étendre les tests de validation des dates, rejets et indicateurs, puis examiner l'historique avec `gitleaks` et documenter le modèle de menaces.
4. Remplacer SQLite et `SequentialExecutor` pour une orchestration durable ; ne pas présenter la configuration Airflow locale comme prête pour la production.

Ne pas supposer qu'une tâche est encore à faire si le dépôt montre qu'elle est terminée. Pour les questions de branche, fusion ou état distant, vérifier GitHub ou les références distantes disponibles ; ne pas déduire une fusion du seul nom de branche.

## Workflow Git

- Une branche par fonctionnalité, avec un nom comme `feat/<nom>`.
- Avant toute opération Git qui prépare un commit, exécuter `git status` et examiner les changements.
- Ajouter uniquement les fichiers concernés, par exemple `git add app/dashboard.py requirements.txt` si ce sont les seuls fichiers de la tâche. Ne jamais ajouter `.env` et ne jamais faire `git add .`.
- Ne pas créer de commit, pousser une branche ou modifier l'historique sauf demande explicite. Une PR vers `main` doit être relue par le binôme.
- L'authentification HTTPS GitHub par mot de passe n'est pas prise en charge : utiliser une clé SSH ou un token géré par l'utilisateur, sans demander ni recopier le secret dans le chat.