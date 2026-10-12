# Prompt — Claude sur l'hôte Proxmox (Sprint 1, piloté par Trello)

## Mode d'emploi (pour l'équipe)

1. Avoir l'accès de secours OVH prêt (console KVM/IPMI ou mode rescue) avant toute
   modification réseau.
2. Sur l'hôte Proxmox, en root :
   ```bash
   cd /root
   git clone -b claude/proxmox-project-automation-92ijpn https://github.com/kiinglemon/proxmox_gpe.git
   cd /root/proxmox_gpe
   git config user.name  "<ton nom>"
   git config user.email "<ton email>"
   ```
   Prévoir un moyen de pousser (clé de déploiement ou token GitHub).
3. Lancer Claude Code depuis `/root/proxmox_gpe`, connecté en SSH depuis ton poste
   (pour que ton IP d'admin soit détectable), en mode de permissions par défaut
   (validation de chaque commande). Ne pas utiliser de mode qui saute les validations.
4. Vérifier avec `/mcp` que le connecteur Trello est disponible.
5. Coller le prompt ci-dessous.

## Liens

- Tableau Trello : https://trello.com/b/Iu8tdCzN/gpe-infraone
- Dépôt GitHub : https://github.com/kiinglemon/proxmox_gpe/tree/claude/proxmox-project-automation-92ijpn
- Spécification : https://github.com/kiinglemon/proxmox_gpe/blob/claude/proxmox-project-automation-92ijpn/docs/specs/PROMPT_InfraOne_v2.md

## Prompt (à copier)

````text
# MISSION — Exécuter le Sprint 1 d'InfraOne sur l'hôte Proxmox, piloté par Trello

Tu es ingénieur DevOps/SecOps et tu travailles DIRECTEMENT sur l'hôte Proxmox VE
(serveur bare metal OVH) du projet InfraOne (TIC-GPE5). Tu suis le tableau Trello
« GPE-INFRAONE » et tu appliques son workflow à CHAQUE carte, sans exception.

## 0. SOURCES DE VÉRITÉ
- Spécification complète (à lire EN ENTIER avant toute action) :
  /root/proxmox_gpe/docs/specs/PROMPT_InfraOne_v2.md
  (en ligne : https://github.com/kiinglemon/proxmox_gpe/blob/claude/proxmox-project-automation-92ijpn/docs/specs/PROMPT_InfraOne_v2.md)
  Chaque carte Trello cite la section (§) concernée.
- Dépôt git : /root/proxmox_gpe (https://github.com/kiinglemon/proxmox_gpe),
  branche de base `claude/proxmox-project-automation-92ijpn`.
  Le backend FastAPI existant est dans backend/app, les scripts dans setup/,
  les playbooks dans ansible/, la doc dans docs/.
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
  SOPS + age. Tokens Proxmox avec les droits minimaux.
- Anti-drift : toute configuration durable doit être reproductible par le code du
  dépôt (scripts idempotents, Ansible, OpenTofu). Les commandes manuelles sont
  réservées au diagnostic.
- Git : une branche par carte, pas de push forcé, pas de Pull Request sans mon
  accord.

## 2. ÉTAPE 0 — DÉCOUVERTE (lecture seule, OBLIGATOIRE)
Avant tout changement, collecte puis présente-moi un état des lieux :
pveversion ; CPU, RAM, disques (lsblk, pvesm status, df -h) ; réseau (ip a,
/etc/network/interfaces, routes) ; dépôts apt configurés ; VMs et conteneurs
existants (qm list, pct list) ; utilisateurs et tokens PVE (pveum) ; état des
firewalls ; services exposés (ss -tlnp) ; IP d'admin détectée. Compare avec la
spécification (32 Go, NVMe, OVH), signale les écarts, puis propose un plan ordonné
pour le sprint. ATTENDS mon « GO » avant toute modification.

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
     — Branche : feat/US-1xx-<slug> ».
   - Crée la branche `feat/US-1xx-<slug>` depuis `claude/proxmox-project-automation-92ijpn`.
2. AVANCER
   - Pour chaque élément de la checklist « ✅ Tâches » : réalise-le, puis COCHE-le.
   - Après chaque tâche significative, un commentaire court : ce qui a été fait,
     fichiers et commit (hash + lien GitHub), points d'attention.
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
   - Pousse la branche. Mets à jour la documentation concernée (docs/…).
   - Déplace la carte vers « 🧪 À tester » (6acd2ab20568387490dea932).
   - Commente :
     « 🧪 Prêt à tester
       Commits : <hash> sur <branche> (<lien GitHub>)
       Critères :
         1. <critère> → <preuve : commande + résultat>
         2. …
       Comment tester : <étapes reproductibles>
       Doc mise à jour : <fichiers> »
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
  être scripté et idempotent dans le dépôt (setup/ existant à faire évoluer).
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
- US-105 · Worker de jobs : dans le backend FastAPI existant (backend/app). File
  asynchrone, rendu Jinja, tofu/ansible lancés sans shell=True, validation par
  schéma, statuts, runner mock, métriques Prometheus.
- US-123 · Mode mock : faux runner tofu/ansible, exporter synthétique, fausse
  console et faux VPN, démo lancée en une commande.

## 5. DÉMARRAGE
1) Lis la spécification et les cartes de référence ci-dessus.
2) Vérifie l'accès Trello en listant les cartes de « 🎯 Sprint en cours ».
3) Fais l'étape 0 (découverte), présente-moi l'état des lieux et ton plan.
4) Attends mon « GO ».
````
