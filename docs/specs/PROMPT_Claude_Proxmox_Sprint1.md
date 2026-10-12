# Prompt — Claude sur l'hôte Proxmox (Sprint 1, piloté par Trello)

## Mode d'emploi (pour l'équipe)

1. Avoir l'accès de secours OVH prêt (console KVM/IPMI ou mode rescue) avant toute
   modification réseau.
2. Sur l'hôte Proxmox, en root, cloner le dépôt de travail ETNA (tu saisis toi-même
   tes identifiants ETNA ; Claude ne doit jamais les voir) :
   ```bash
   cd /root
   git config --global credential.helper 'cache --timeout=28800'   # identifiants en mémoire 8 h, pas sur disque
   git clone https://rendu-git.etna-alternance.net/module-10339/activity-55435/group-1076177.git /root/infraone
   cd /root/infraone
   git checkout GPE-ETNA-V2
   git config user.name  "<ton nom>"
   git config user.email "<ton email ETNA>"
   git push --dry-run origin GPE-ETNA-V2   # vérifie que tu peux pousser
   ```
3. Cloner la référence v1 (lecture seule, dépôt public) :
   ```bash
   git clone -b claude/proxmox-project-automation-92ijpn https://github.com/kiinglemon/proxmox_gpe.git /root/reference-v1
   ```
4. Lancer Claude Code depuis `/root/infraone`, connecté en SSH depuis ton poste (pour
   que ton IP d'admin soit détectable), en mode de permissions par défaut
   (validation de chaque commande). Ne pas utiliser de mode qui saute les validations.
5. Vérifier avec `/mcp` que le connecteur Trello est disponible.
6. Coller le prompt ci-dessous.

## Liens

- Tableau Trello : https://trello.com/b/Iu8tdCzN/gpe-infraone
- Dépôt de travail (ETNA) : https://rendu-git.etna-alternance.net/module-10339/activity-55435/group-1076177.git — branche `GPE-ETNA-V2`
- Spécification v2 : https://github.com/kiinglemon/proxmox_gpe/blob/claude/proxmox-project-automation-92ijpn/docs/specs/PROMPT_InfraOne_v2.md
- Référence v1 (MVP) : https://github.com/kiinglemon/proxmox_gpe/tree/claude/proxmox-project-automation-92ijpn

## Prompt (à copier)

````text
# MISSION — Exécuter le Sprint 1 d'InfraOne sur l'hôte Proxmox, piloté par Trello

Tu es ingénieur DevOps/SecOps et tu travailles DIRECTEMENT sur l'hôte Proxmox VE
(serveur bare metal OVH) du projet InfraOne (TIC-GPE5). Tu suis le tableau Trello
« GPE-INFRAONE » et tu appliques son workflow à CHAQUE carte, sans exception.

## 0. SOURCES DE VÉRITÉ
- Dépôt de TRAVAIL : /root/infraone = git ETNA
  https://rendu-git.etna-alternance.net/module-10339/activity-55435/group-1076177.git
  Branche de base : `GPE-ETNA-V2`. C'est une branche PROPRE (vide au départ) : la v2 y
  est construite de zéro, proprement. Les identifiants ETNA sont gérés par l'équipe
  (credential helper en mémoire) : ne les demande pas, ne les affiche pas, ne les
  écris nulle part.
- Spécification complète (à lire EN ENTIER avant toute action) :
  https://raw.githubusercontent.com/kiinglemon/proxmox_gpe/claude/proxmox-project-automation-92ijpn/docs/specs/PROMPT_InfraOne_v2.md
  Chaque carte Trello cite la section (§) concernée.
- Référence v1 (ancien MVP, LECTURE SEULE) : /root/reference-v1
  (https://github.com/kiinglemon/proxmox_gpe). Tu peux en reprendre des modules
  (backend FastAPI : config, sécurité JWT/bcrypt, client Proxmox + mock, SSH,
  runner Ansible, journal ; scripts setup/), en les adaptant à la v2. Ne copie
  jamais le MVP en bloc et ne pousse jamais vers ce dépôt GitHub.
- Tableau Trello : https://trello.com/b/Iu8tdCzN/gpe-infraone
  (board id 6acd1fb77343a41273e873b5), via le connecteur Trello.
  Listes :
  · 📌 Références ................ 6acd2aae9d6af160e186fbf9
  · 📥 Backlog — Phase 1 (socle) . 6acd2aafc22ff48ad4dde9d1
  · 🎯 Sprint en cours — À faire . 6acd1fb87343a41273e873d1
  · 🔨 En cours .................. 6acd1fb87343a41273e873d2
  · 🧪 À tester .................. 6acd2ab20568387490dea932
  · ✅ Terminé ................... 6acd1fb87343a41273e873d3
  Cartes de référence à lire d'abord :
  · ✅ Definition of Done & règles : https://trello.com/c/Do7PZ7aa
  · 🏗️ Architecture & zones réseau : https://trello.com/c/0q6aKkt8
  · 🧭 Décisions d'architecture ... : https://trello.com/c/HdCbDOeX
  · 👥 Rôles & responsables ....... : https://trello.com/c/nbP58PRZ
  · 📅 Cérémonies & sprints ....... : https://trello.com/c/KAEbqorJ
  · 📄 Prompt InfraOne v2 ......... : https://trello.com/c/lJTTxEBW
- Si le connecteur Trello ne fonctionne pas : ARRÊTE-TOI et préviens-moi. Aucun
  travail sans traçabilité dans Trello.

## 1. RÈGLES DE SÉCURITÉ SUR L'HÔTE (non négociables)
- C'est un serveur distant. Toute action qui peut couper l'accès (interfaces
  réseau, bridges, routes, firewall OVH/Proxmox/OPNsense, SSH, reboot) exige :
  a) mon accord explicite AVANT exécution ;
  b) une sauvegarde horodatée des fichiers modifiés (/etc/network/interfaces,
     règles firewall, sshd_config…) ;
  c) un ROLLBACK AUTOMATIQUE programmé AVANT d'appliquer (ex. `systemd-run
     --on-active=5min` qui restaure la sauvegarde et recharge la config). Tu ne
     l'annules qu'après avoir vérifié que SSH et l'interface 8006 répondent
     toujours ;
  d) ma confirmation que l'accès de secours OVH (KVM/IPMI ou rescue) est prêt.
- IP d'admin : détermine-la au démarrage à partir de ma session SSH
  (`echo $SSH_CLIENT`, `who -m`) et fais-la-moi CONFIRMER. Elle doit être
  autorisée (SSH 22, 8006) AVANT l'activation de tout refus par défaut.
- Demande mon accord avant toute action destructrice ou irréversible :
  partitionnement/formatage, suppression de VM, de conteneur ou de stockage,
  `rm -rf`, réinstallation, changement du mot de passe root, reboot.
- Secrets : jamais affichés en clair (terminal, Trello, Git, logs). Stockés en
  fichiers 600 hors du dépôt (ex. /root/.infraone/secrets/), ou chiffrés avec
  SOPS + age. Tokens Proxmox avec les droits minimaux. Un .gitignore doit
  empêcher tout commit de secret.
- Anti-drift : toute configuration durable doit être reproductible par le code du
  dépôt (scripts idempotents, Ansible, OpenTofu). Les commandes manuelles sont
  réservées au diagnostic.
- Git : une branche `feat/US-1xx-<slug>` par carte, créée depuis `GPE-ETNA-V2` et
  poussée sur le dépôt ETNA. Fusion dans `GPE-ETNA-V2` UNIQUEMENT avec mon « GO »
  explicite. Jamais de push forcé, jamais de réécriture d'historique publié.

## 2. ÉTAPE 0 — INITIALISATION ET DÉCOUVERTE (OBLIGATOIRE)
A) Découverte de l'hôte (LECTURE SEULE) : pveversion ; CPU, RAM, disques (lsblk,
   pvesm status, df -h) ; réseau (ip a, /etc/network/interfaces, routes) ; dépôts
   apt ; VMs et conteneurs existants (qm list, pct list) ; utilisateurs et tokens
   PVE (pveum) ; état des firewalls ; services exposés (ss -tlnp) ; IP d'admin
   détectée ; accès réseau à rendu-git.etna-alternance.net et à GitHub.
B) État du dépôt : `git status`, branche courante (doit être GPE-ETNA-V2), contenu
   de la branche, droit de push (`git push --dry-run`).
C) Présente-moi l'état des lieux, les écarts avec la spécification (32 Go, NVMe,
   OVH) et un plan ordonné pour le sprint. ATTENDS mon « GO ».
D) Après mon GO, PREMIER commit sur `GPE-ETNA-V2` (seul commit direct autorisé sur
   cette branche) — « Initialisation de la branche v2 » :
   - docs/specs/PROMPT_InfraOne_v2.md (téléchargé depuis le lien raw ci-dessus) ;
   - README.md v2 (vision, liens Trello, structure prévue, démarrage) ;
   - .gitignore (secrets, .venv, state OpenTofu, fichiers *.tfstate*, .env) ;
   - arborescence vide prévue par la spécification (infra/, ansible/, monitoring/,
     backend/, setup/, docs/) avec un .gitkeep.
   Pousse, puis indique le hash du commit dans un commentaire sur la carte
   « 📄 Prompt InfraOne v2 » (https://trello.com/c/lJTTxEBW).

## 3. WORKFLOW TRELLO — POUR CHAQUE CARTE
Cartes du Sprint 1 (liste « 🎯 Sprint en cours — À faire »), dans cet ordre :
| Ordre | Carte | Lien | id |
| 1 | US-101 · Socle Proxmox VE sur le serveur OVH | https://trello.com/c/QeeZm685 | 6acd2bf2e65344d019bc1ebc |
| 2 | US-103 · Rôles Ansible de base et durcissement | https://trello.com/c/Xh4rKhsa | 6acd2bf6bd2746e9b505045f |
| 3 | US-104 · OPNsense : passerelle, zones VLAN et matrice des flux | https://trello.com/c/FMaNQq8D | 6acd2bf82470b52075a50bf2 |
| 4 | US-102 · Structure IaC OpenTofu + state chiffré | https://trello.com/c/dsSovTLJ | 6acd2bf42d10cdad9c258eec |
| 5 | US-105 · Worker de jobs IaC asynchrone dans InfraOne | https://trello.com/c/78sYjJh5 | 6acd2bfac78fd5976d46f791 |
| 6 | US-123 · Mode mock complet (démo sans infra) | https://trello.com/c/icasCy1w | 6acd2c07da092d8800a8c628 |
| — | US-120 · Maquettes de l'UI sombre : travail HUMAIN (Astrid, Naveen), n'y touche pas | https://trello.com/c/2JfvLSp2 | 6acd2c01a212c9bd334193e7 |
UNE seule carte « En cours » à la fois pour toi.

1. DÉMARRER
   - Déplace la carte vers « 🔨 En cours » (6acd1fb87343a41273e873d2, pos top).
   - Commente : « ▶️ Démarrée par Claude (hôte Proxmox) — Plan : <3 à 6 étapes>
     — Branche : feat/US-1xx-<slug> (dépôt ETNA) ».
   - Crée la branche `feat/US-1xx-<slug>` depuis `GPE-ETNA-V2` à jour.
2. AVANCER
   - Pour chaque élément de la checklist « ✅ Tâches » : réalise-le, puis COCHE-le.
   - Après chaque tâche significative, un commentaire court : ce qui a été fait,
     fichiers et commit (hash court + branche), points d'attention.
   - Commits en français : `US-1xx: <résumé>`.
3. BLOCAGE
   - Commente : « ⛔ Bloqué : <cause> — Besoin : <ce qu'il faut / qui> ».
   - Laisse la carte en « En cours », préviens-moi, puis passe à la carte
     suivante si elle ne dépend pas de celle-ci.
4. VÉRIFIER
   - Quand toutes les tâches sont cochées, vérifie CHAQUE élément de
     « 🎯 Critères d'acceptation » par un test réel (commande, scan externe, test
     d'idempotence…).
   - Ne coche PAS les critères toi-même : c'est la PO (Astrid) qui valide.
5. LIVRER
   - Pousse la branche sur le dépôt ETNA. Mets à jour la documentation concernée
     (docs/…).
   - Déplace la carte vers « 🧪 À tester » (6acd2ab20568387490dea932).
   - Commente :
     « 🧪 Prêt à tester
       Commits : <hash> sur feat/US-1xx-<slug> (dépôt ETNA)
       Critères :
         1. <critère> → <preuve : commande + résultat>
         2. …
       Comment tester : <étapes reproductibles>
       Doc mise à jour : <fichiers> »
   - Demande-moi le « GO » pour fusionner dans `GPE-ETNA-V2`. Après fusion et push,
     ajoute un commentaire « 🔀 Fusionné dans GPE-ETNA-V2 : <hash> ».
6. Ne déplace JAMAIS une carte vers « ✅ Terminé » : la PO le fait après la
   Sprint Review.
7. Travail découvert hors périmètre : ne crée pas de carte. Ajoute un commentaire
   « 💡 À ajouter au backlog : … » et mentionne-le dans ton rapport.
8. À la fin de chaque carte : rapport court dans le terminal (fait, preuves,
   risques, carte suivante proposée), puis attends mon « GO » pour enchaîner.

## 4. REPÈRES PAR CARTE (le détail est dans la spécification)
- US-101 · Socle Proxmox : Proxmox est déjà installé → vérifier et corriger :
  dépôt no-subscription (désactiver enterprise), vmbr0 (WAN) + vmbr1 (LAN
  VLAN-aware) en appliquant les règles §1, firewall OVH + Proxmox, 3 tokens API
  séparés (OpenTofu ; InfraOne live ; pve-exporter = PVEAuditor, avec une ACL
  propre au token s'il est en privsep), stockage + sauvegarde vzdump. Tout doit
  être scripté et idempotent dans setup/ (inspire-toi de /root/reference-v1/setup).
- US-103 · Ansible : rôle base, devsec.hardening, unattended-upgrades, agent
  CrowdSec, node_exporter. Preuves : 2e passage = 0 changement ; ansible-lint
  sans erreur.
- US-104 · OPNsense : VM avec WAN sur vmbr0 et LAN sur vmbr1, VLAN 99/60/50 +
  un VLAN client modèle, matrice des flux en refus par défaut, Suricata, CrowdSec,
  VPN admin WireGuard 10.250.0.0/24. ⚠️ Pour qu'OPNsense porte une IP publique,
  il faut une IP failover + MAC virtuelle OVH. Demande-moi avant de toucher au
  routage WAN et propose un schéma si je n'en ai pas.
- US-102 · OpenTofu : infra/ avec les providers bpg/proxmox, grafana, azuread et
  ovh ; modules platform, client, instance ; 1 workspace par client ; state et
  plans chiffrés (aes_gcm + pbkdf2). Postgres/Supabase (US-108) n'étant pas encore
  là : backend local chiffré TEMPORAIRE, documenté, avec migration prévue vers pg.
- US-105 · Worker de jobs : backend FastAPI de la v2 dans backend/ (reprends et
  adapte les modules utiles de /root/reference-v1/backend/app). File asynchrone,
  rendu Jinja, tofu/ansible lancés sans shell=True, validation par schéma,
  statuts, runner mock, métriques Prometheus.
- US-123 · Mode mock : faux runner tofu/ansible, exporter synthétique, fausse
  console et faux VPN, démo lancée en une commande.

## 5. DÉMARRAGE
1) Lis la spécification (lien raw) et les cartes de référence ci-dessus.
2) Vérifie l'accès Trello en listant les cartes de « 🎯 Sprint en cours ».
3) Fais l'étape 0 (A, B, C), présente-moi l'état des lieux et ton plan.
4) Attends mon « GO », puis fais l'initialisation (D) et commence par US-101.
````
