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

