# Méthodologie de projet — InfraOne (TIC-GPE5)

Synthèse de la méthodologie Agile du projet **INFRA One**, alignée sur le
document de référence `TICGPE5_Methodologie_v6_MVP`. Ce fichier sert de
référence rapide pour l'équipe et met en correspondance la méthodologie avec le
code de ce dépôt.

## Recentrage du périmètre

InfraOne ne vise plus à couvrir toute la gestion d'un parc PME dès la première
année, mais à démontrer un **MVP réaliste** : le déploiement d'une VM Linux
depuis une interface web, avec configuration simple, connexion SSH et gestion
minimale des erreurs.

**Périmètre MVP (Version n)** :
- Déployer une VM Linux depuis l'interface web
- Se connecter en SSH à la VM déployée
- Générer un journal de logs d'erreur formalisé
- Modifier/configurer une VM : CPU, RAM, disque, image Linux
- Déployer un service avec configuration de base
- Authentification simple à la plateforme

## 1. Méthodologie : Scrum + Kanban

**Scrum** comme cadre principal (sprints de 2 semaines), complété par **Kanban**
(limitation du WIP, visualisation du flux : À faire / En cours / À tester /
Terminé) pour les petits items entre sprints.

## 2. Organisation de l'équipe

| Membre(s) | Rôle Scrum | Domaine technique |
|-----------|-----------|-------------------|
| Astrid | Product Owner & Testeuse | Vision produit, US & UX, maquettes Figma, priorisation, QA/tests |
| Edry / Yanis | Équipe de dev | Backend / API, Python/FastAPI, tests unitaires, orchestration infra |
| Edry / Astrid / Glodi / Randy | Équipe de dev | Infra & IaC, Ansible, Proxmox, sécurité réseau |
| Naveen | Équipe de dev | Frontend Dashboard, React/Tailwind, intégration API |
| Glodi / Randy | Équipe de dev | CI/CD & DevSecOps, GitLab CI, tests de déploiement, doc |
| Tournant | Scrum Master | Facilite les cérémonies, lève les obstacles |

**Artéfacts** : Product Backlog, Sprint Backlog, Burndown Chart, Tableau Kanban,
Incrément. **Cérémonies** : Sprint Planning, Daily Scrum, Sprint Review,
Rétrospective.

## 3. Épics

| N° | Épic | Périmètre |
|----|------|-----------|
| E1 | Connexion | Authentification des administrateurs — **MVP** |
| E2 | Provisioning Infrastructure | Création/config des VMs Linux — **MVP** |
| E3 | Enrollment machine | Scan réseau, inventaire — *n+1* |
| E4 | Install Services | Déploiement d'un service (base **MVP**, avancé *n+1*) |
| E5 | Supervision & Alerting | Dashboard temps réel, alertes — *n+1* |
| E6 | Sécurité & Conformité | Audit, logs d'actions — *n+1* |
| E7 | Configuration | Paramètres globaux, sauvegarde/restauration — *n+2* |
| E8 | Active Directory | Utilisateurs, groupes, règles AD — *n+2* |
| E9 | Contact support | Contacter l'équipe support |

## 4. Prérequis techniques

**Recommandé par le document** : machine hôte Proxmox, 64 Go RAM, ~1 To de
stockage, réseau local + Internet, compte root exploitable via l'API Proxmox.

> **Contexte réel de ce déploiement** : hôte neuf de **10 Go RAM / 4 vCPU**.
> Le script d'installation (`setup/`) calibre automatiquement les valeurs par
> défaut et les garde-fous pour rester dans ces limites (VM modestes, 1 à 2 VM
> concurrentes réalistes).

## 5. Hyperviseur : Proxmox VE

Retenu car open source et gratuit, bien documenté, compatible Linux, doté d'une
**API REST complète** (intégration FastAPI) et d'une interface web native.
InfraOne ne remplace pas Proxmox : il ajoute une couche d'automatisation et de
simplification au-dessus.

## 6. Hors périmètre MVP (vision n+1 / n+2)

VM Windows, scan réseau automatique complet, enrôlement auto, monitoring avancé,
alertes automatiques, intégration Active Directory, sauvegarde/restauration
automatique, HA/clustering multi-hôtes, VLAN, configuration avancée des services.

## 7. Backlog priorisé (POC / Version n)

Priorités : 🔴 Critique · 🟠 Haute · 🟡 Moyenne · 🟢 Faible (n+1).
La complexité est en points (plus le chiffre est élevé, plus la US est complexe).

| ID | User Story | Compl. | Priorité | Statut dans ce dépôt |
|----|-----------|--------|----------|----------------------|
| US-001 | Se connecter (login/mot de passe) | 5 | 🔴 | ✅ implémentée |
| US-002 | Réinitialiser mot de passe oublié | 3 | 🟠 | ✅ implémentée (email non branché) |
| US-003 | Créer une VM (template, CPU/RAM/disque) | 8 | 🔴 | ✅ implémentée |
| US-004 | Modifier la config d'une VM | 8 | 🔴 | ✅ implémentée |
| US-005 | Tester la connexion SSH | 5 | 🔴 | ✅ implémentée |
| US-006 | Consulter les logs d'erreur InfraOne | 8 | 🔴 | ✅ implémentée |
| US-007 | Déployer un service (Nginx/Apache) | 8 | 🔴 | ✅ implémentée (Ansible) |
| US-008..018 | Inventaire, supervision, AD, audit… | — | 🟢 | Vision n+1 / n+2 |

## 8. Calendrier des sprints

| Sprint | Objectif principal |
|--------|--------------------|
| S1 | Connexion + base frontend/backend |
| S2 | Connexion Proxmox + création VM Linux simple |
| S3 | Configuration VM : CPU, RAM, disque, image |
| S4 | Logs d'erreur + retour d'état + test SSH |
| S5 | Déploiement service basique + tests + documentation |

## 9. Réponses de ce dépôt aux blocages des rétrospectives

- **« Environnement Proxmox non configuré »** → `setup/` automatise entièrement
  la mise en place (token API + template cloud-init) en une commande.
- **« Aucune VM disponible pour démontrer »** → **mode mock** (`--mock`) pour
  démontrer l'app sans infra.
- **« Compatibilité bcrypt/passlib »** → on utilise `bcrypt` directement, sans
  passlib, pour éviter ce conflit.
- **« Installations d'environnement à anticiper »** → `10-host-packages.sh`
  installe tous les prérequis automatiquement.
