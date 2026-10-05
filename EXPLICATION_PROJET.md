# Projet financial-sec-pipeline

## 1. Objectif du projet

Ce projet est une plateforme de Data Engineering appliquée au marché financier. Son but est de :

- récupérer des données boursières et crypto via Yahoo Finance,
- nettoyer et valider ces données,
- calculer des indicateurs techniques,
- les stocker dans PostgreSQL,
- les exposer dans un dashboard Streamlit,
- sécuriser l’accès avec un système d’authentification et des rôles,
- suivre les actions via des logs d’audit,
- orchestrer le pipeline avec Airflow.

L’objectif pédagogique est de montrer un pipeline complet, réaliste, avec des éléments de cybersécurité et de gestion des données.

---

## 2. Architecture globale

Le flux principal est le suivant :

Yahoo Finance -> extract -> transform -> load -> PostgreSQL -> dashboard Streamlit

Les composants principaux sont :

- `etl/extract.py` : récupération des données externes,
- `etl/transform.py` : nettoyage et validation,
- `etl/load.py` : persistance dans PostgreSQL,
- `sql/init/01_init.sql` : schéma de base des données,
- `sql/init/02_security.sql` : tables d’authentification,
- `sql/init/03_application_roles.sh` : création des comptes applicatifs,
- `app/dashboard.py` : interface utilisateur,
- `security/auth.py` : authentification et verrouillage,
- `security/database.py` : connexion PostgreSQL sécurisée,
- `dags/market_pipeline.py` : DAG Airflow,
- `docker-compose.yml` : orchestration locale.

---

## 3. Les données traitées

Le projet suit principalement 3 actifs :

- `AAPL`
- `MSFT`
- `BTC-USD`

Les données récupérées incluent typiquement :

- date,
- ouverture,
- maximum,
- minimum,
- fermeture,
- volume,
- symbole.

Les données sont supposées non fiables par défaut. Il faut donc les valider avant stockage.

---

## 4. Extraction des données

Le fichier `etl/extract.py` récupère les séries historiques via `yfinance`.

### Ce que cela fait

- appelle l’API Yahoo Finance,
- récupère les données de prix historiques,
- normalise les colonnes,
- renvoie des DataFrames prêts à être transformés.

### Pourquoi c’est important

Les données de marché sont dynamiques, parfois incomplètes, parfois incohérentes. Il faut donc les traiter comme des données non fiables.

### Sécurité / robustesse

- rejet des entrées invalides,
- validation de symboles,
- validation des dates et du volume,
- pas de confiance aveugle dans la source externe.

---

## 5. Transformation et validation

Le cœur du traitement est dans `etl/transform.py`.

### 5.1 Nettoyage

La fonction `clean_data` :

- supprime les lignes inutiles,
- normalise les colonnes,
- garde les colonnes nécessaires,
- traite les valeurs manquantes ou aberrantes.

### 5.2 Validation

La fonction `validate_data` vérifie :

- les prix strictement positifs,
- cohérence OHLC : `open`, `high`, `low`, `close`,
- volume positif ou nul,
- date non future,
- symbole dans la liste autorisée,
- lignes invalides rejetées proprement.

### 5.3 Indicateurs calculés

La fonction `compute_indicators` calcule :

- `daily_return` : rendement journalier en pourcentage,
- `volatility` : écart-type glissant des rendements,
- `moving_avg` : moyenne mobile sur 5 périodes.

Ce sont des métriques classiques en analyse technique.

### Pourquoi c’est utile

Les données brutes ne sont pas directement exploitables pour la décision. Les indicateurs permettent :

- mesurer la performance,
- comparer les actifs,
- visualiser les tendances,
- détecter des anomalies.

---

## 6. Chargement dans PostgreSQL

Le fichier `etl/load.py` sert à écrire les données dans la base.

### Rôle

- charger les actifs,
- charger les prix,
- charger les indicateurs,
- enregistrer les événements d’audit.

### Idempotence

Le chargement est pensé pour éviter les doublons :

- les données existaient déjà,
- on remet les mêmes informations,
- l’insertion ne doit pas créer de répétition.

### Audit

Le code enregistre dans `audit_logs` :

- actions utilisateur,
- détails,
- statut,
- horodatage.

Cela est très utile pour le suivi de sécurité et la traçabilité.

---

## 7. Base de données PostgreSQL

Le schéma est défini dans `sql/init/01_init.sql`.

### Tables principales

#### `assets`
Contient les actifs suivis : symboles, noms, types.

Exemple :

- AAPL
- MSFT
- BTC-USD

#### `asset_prices`
Contient les prix historiques :

- `asset_id`
- `price_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`

#### `indicators`
Contient les métriques dérivées sur chaque date :

- `daily_return`
- `volatility`
- `moving_avg`

#### `audit_logs`
Stocke les événements importants :

- authentification réussie,
- échec de connexion,
- actions utilisateur,
- journaux de sécurité.

---

## 8. Sécurité du projet

C’est l’une des parties importantes du dépôt.

### 8.1 Authentification

Le fichier `security/auth.py` contient :

- `normalize_username`
- `hash_password`
- `verify_password`
- `authenticate`

### Qu’est-ce qui est fait

- les mots de passe ne sont pas stockés en clair,
- on stocke un hash bcrypt,
- on vérifie le mot de passe à la connexion,
- on limite les tentatives répétées,
- on verrouille un compte temporairement après 5 échecs.

### Menace visée

- brute force,
- usurpation de compte,
- utilisation de mots de passe faibles.

### Défense appliquée

- bcrypt avec sel,
- verrouillage après 5 échecs,
- journalisation des tentatives et succès,
- politique de mot de passe minimale.

### 8.2 Rôle d’utilisateur

Le système prévoit des rôles :

- `analyst`
- `auditor`

Cela permet de séparer :

- lecture de données marché,
- lecture de log d’audit,
- actions d’administration.

### Ce que cela protège

- un analyste ne doit pas forcément voir tous les éléments sensibles,
- un auditeur peut avoir accès aux journaux,
- les contrôles doivent être côté application et côté base de données.

### 8.3 Journal d’audit

`audit_logs` est crucial pour :

- suivre les connexions,
- suivre les actions sensibles,
- faire du forensic,
- vérifier les erreurs de sécurité.

---

## 9. Gestion de PostgreSQL et rôles applicatifs

Le script `sql/init/03_application_roles.sh` configure les comptes de base utilisés par les services.

### Rôles créés

- un compte pour le dashboard,
- un compte pour l’ETL.

### Principe

- le dashboard a des droits de lecture minimaux,
- l’ETL a des droits d’écriture nécessaires,
- on évite les comptes avec trop de privilèges.

### Pourquoi c’est important

En sécurité, le principe du moindre privilège est fondamental :

- un service ne doit pas avoir plus de droits que nécessaire.

---

## 10. Dashboard Streamlit

Le fichier `app/dashboard.py` est l’interface utilisateur.

### Il affiche

- les prix des actifs,
- les indicateurs,
- les tendances,
- les journaux d’audit,
- selon le rôle de l’utilisateur.

### Il gère aussi

- connexion utilisateur,
- validation d’identité,
- affichage conditionnel selon le rôle,
- protection logique de l’accès.

### Important

Le dashboard ne doit pas être la seule protection. Le contrôle d’accès doit être aussi appliqué côté base de données et côté logique applicative.

---

## 11. Airflow

Le DAG dans `dags/market_pipeline.py` représente le pipeline quotidien :

- extract
- transform
- load

### Ce que cela apporte

- automatisation du flux,
- répétition et traçabilité,
- travail planifié sur des données de marché.

### Limite actuelle

Dans ce projet, l’exécution est locale et en mode pédagogique, avec :

- `SequentialExecutor`
- SQLite local

C’est fonctionnel pour un environnement d’apprentissage, mais pas pour un usage de production robuste.

### Ce qu’il faut en production

- base PostgreSQL dédiée à Airflow,
- exécuteur plus robuste,
- logs centralisés,
- gestion des dépendances et des retries.

---

## 12. Conteneurisation Docker

Le fichier `docker-compose.yml` lance :

- PostgreSQL,
- le dashboard Streamlit,
- Airflow.

### Avantages

- cohérence entre machines,
- reproduction plus facile,
- isolation des services,
- exécution locale proche de l’environnement cible.

### Bonnes pratiques visibles

- PostgreSQL non exposé au monde,
- ports limités,
- services distincts,
- variables d’environnement centralisées.

---

## 13. Gestion des secrets

Le projet utilise un fichier `.env` pour stocker les variables sensibles.

### Ce qui est important

- le `.env` ne doit pas être versionné,
- il ne doit pas être ajouté au dépôt Git,
- les mots de passe et clés sensibles doivent rester locaux.

### Exemple de variables

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DASHBOARD_DB_USER`
- `DASHBOARD_DB_PASSWORD`
- `ETL_DB_USER`
- `ETL_DB_PASSWORD`

En pratique, on garde seulement des valeurs de démonstration dans `.env.example` et les vraies valeurs dans `.env` local.

---

## 14. Pourquoi ce projet est intéressant

Il combine plusieurs domaines :

- Data Engineering : pipelines ETL et ingestion,
- Data Quality : validation et nettoyage,
- Cybersecurity : auth, RBAC, logs d’audit,
- DevOps : Docker, orchestration, environnement local,
- Data Visualization : dashboard Streamlit,
- Automation : Airflow.

C’est un très bon projet pour montrer qu’on sait travailler sur une application complète, pas seulement sur un script Python isolé.

---

## 15. Points forts du projet

- flux ETL réel,
- validation des données,
- stockage structuré,
- sécurité appliquée,
- gestion des rôles,
- logs d’audit,
- dockerisation,
- automatisation du pipeline,
- interface de visualisation.

---

## 16. Points de vigilance

Le projet est solide pour un contexte pédagogique, mais il y a des limites à connaître :

- Airflow est encore en mode pédagogique,
- la base de données locale doit être bien initée,
- les secrets doivent rester hors Git,
- les rôles doivent être vérifiés de manière stricte,
- les accès ne doivent pas reposer uniquement sur de simples masquages UI.

---

## 17. Conclusion

Ce projet est une démonstration d’un pipeline de données financier avec une forte composante sécurité. Il montre comment on peut :

- extraire des données externes,
- les transformer et les valider,
- les stocker proprement,
- les afficher dans un dashboard,
- sécuriser l’accès,
- auditer les actions,
- automatiser le traitement.

C’est un projet de type “full stack data” avec une vraie logique de sécurité et de gouvernance des données.

---

## 18. Identifiants de test

Pour accéder au dashboard en local :

- identifiant : `demo`
- mot de passe : `DemoPass12345!`

---

## 19. Liens utiles dans le dépôt

- [etl/extract.py](etl/extract.py)
- [etl/transform.py](etl/transform.py)
- [etl/load.py](etl/load.py)
- [app/dashboard.py](app/dashboard.py)
- [security/auth.py](security/auth.py)
- [security/database.py](security/database.py)
- [sql/init/01_init.sql](sql/init/01_init.sql)
- [sql/init/02_security.sql](sql/init/02_security.sql)
- [sql/init/03_application_roles.sh](sql/init/03_application_roles.sh)
- [docker-compose.yml](docker-compose.yml)
- [dags/market_pipeline.py](dags/market_pipeline.py)
- [tests/test_transform.py](tests/test_transform.py)
- [tests/test_auth.py](tests/test_auth.py)
