1 Financial Security Pipeline

Pipeline de Data Engineering orienté finance, qui récupère automatiquement
des données de marché (actions, crypto), les nettoie, calcule des indicateurs
financiers clés, et les stocke dans une base PostgreSQL — avec une couche de
sécurité (authentification, rôles, journalisation) pour se rapprocher des
standards d'une architecture professionnelle.

2 Objectif du projet

Ce projet a été conçu pour démontrer une chaîne complète de Data Engineering,
de l'extraction de données brutes jusqu'à leur exploitation via un dashboard,
en intégrant des bonnes pratiques de cybersécurité (gestion des accès,
audit des actions, contrôle qualité des données).

3 Fonctionnalités principales

- Extraction automatique de données financières (prix, volumes) via API (Yahoo Finance)
- Nettoyage et transformation des données avec Python (pandas)
- Calcul d'indicateurs financiers : rendement journalier, volatilité, moyenne mobile
- Stockage structuré dans PostgreSQL
- Orchestration et automatisation quotidienne avec Apache Airflow
- Dashboard web pour consulter les données, rechercher des actifs et visualiser les indicateurs
- Authentification, gestion des rôles/permissions et journalisation des actions (audit logs)
- Conteneurisation avec Docker pour un déploiement reproductible

4 Stack technique

## Lancer le projet en local

Ajoutez dans votre fichier `.env` les paramètres `DASHBOARD_DB_USER`, `DASHBOARD_DB_PASSWORD`, `ETL_DB_USER` et `ETL_DB_PASSWORD` avec des identifiants propres à l'environnement local. Ne copiez pas les valeurs d'exemple telles quelles et ne versionnez jamais `.env`.

```sh
source venv/bin/activate
docker compose up --build -d
```

Le dashboard est disponible sur `http://localhost:8501` et Airflow sur `http://localhost:8080`. Airflow tourne en mode `standalone` avec SQLite : cette configuration est destinée au développement local, pas à la production. Sa base de métadonnées est temporaire et sera recréée si le conteneur est supprimé/recréé. Son compte initial est généré par Airflow ; consultez les logs du service avec `docker compose logs airflow`.

PostgreSQL n'expose pas le port 5432 sur l'hôte. Pour l'administrer, utilisez `docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"` depuis un shell où les variables sont définies, ou entrez dans le conteneur et lisez-les depuis son environnement.

## Authentification et migration

Sur une base neuve, les scripts SQL créent les tables `users` et `login_attempts` ainsi que des rôles PostgreSQL séparés et limités pour le dashboard et l'ETL. Pour une base déjà initialisée, les scripts d'initialisation PostgreSQL ne sont pas rejoués automatiquement. Après avoir ajouté les quatre variables `DASHBOARD_DB_*` et `ETL_DB_*` à `.env`, appliquez la migration et créez les rôles applicatifs :

```sh
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/02_security.sql'
docker compose exec postgres sh -c 'sh /docker-entrypoint-initdb.d/03_application_roles.sh'
```

Créez les comptes de dashboard depuis le venv et avec les identifiants PostgreSQL de maintenance configurés par `POSTGRES_USER` et `POSTGRES_PASSWORD` :

```sh
venv/bin/python -m security.create_user mehdi --role analyst
venv/bin/python -m security.create_user auditeur --role auditor
```

Les mots de passe sont demandés de façon interactive et stockés sous forme bcrypt. Après cinq échecs, l'identifiant est verrouillé pendant quinze minutes. Le rôle Analyste voit le marché et les indicateurs ; le rôle Auditeur voit aussi les logs. La connexion SQL du dashboard utilise `URL.create` et les valeurs des requêtes restent paramétrées.

## Tests et sécurité

```sh
venv/bin/python -m pytest tests/
```

La CI exécute ces tests et Gitleaks sur l'historique Git. Si l'extraction est refusée par la source, respecte ses conditions d'accès et arrête ou espace les requêtes ; le pipeline ne cherche pas à usurper un navigateur ou à contourner une protection anti-bot.

