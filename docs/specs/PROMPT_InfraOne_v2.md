# MISSION — InfraOne v2 : plateforme d'infogérance pilotée par IaC
# (OpenTofu/Ansible) pour prestataire informatique : accès clients sécurisé,
# catalogue de services, postes Windows (Samba AD / Entra ID), déploiement
# d'images, monitoring automatique multi-clients (Prometheus/Grafana),
# sécurité renforcée, UI sombre, documentation.

Tu es ingénieur DevOps / SecOps / full-stack. Tu construis la v2 du projet InfraOne
(TIC-GPE5, "Projet INFRA One") sur une BRANCHE PROPRE.
- Dépôt de travail : git ETNA
  https://rendu-git.etna-alternance.net/module-10339/activity-55435/group-1076177.git
  Branche de base : `GPE-ETNA-V2` (vide au départ : la v2 y est construite proprement).
- Référence (ancien MVP v1, à réutiliser PAR MORCEAUX si utile, jamais copié en bloc) :
  https://github.com/kiinglemon/proxmox_gpe/tree/claude/proxmox-project-automation-92ijpn
Livre PAR PHASES (section 14) : termine et teste une phase avant la suivante.

## 0. CONTEXTE & VISION
InfraOne = plateforme web au-dessus de Proxmox VE, utilisée par un PRESTATAIRE
INFORMATIQUE (infogérance de PME) pour : provisionner l'infra de ses clients, leur
proposer un catalogue de services, gérer leurs postes Windows (domaine, déploiement
d'images), et SUPERVISER AUTOMATIQUEMENT tout ce qui est créé. Multi-clients,
cloisonnement strict.
Référence v1 réutilisable (dépôt GitHub ci-dessus) : backend FastAPI (Python), auth
JWT, logs formalisés, abstraction backend (Proxmox + Mock), SSH (paramiko), runner
Ansible, UI légère servie par FastAPI, playbooks nginx/apache, setup/ idempotent,
mode MOCK. Reprends les modules utiles en les adaptant à la v2 (multi-tenant, IaC).
CONTRAINTE : Python/FastAPI reste le cœur. Hôte = Proxmox VE sur OVH bare metal.

## 1. MODÈLE IaC — TOUT PILOTÉ PAR OPENTOFU/ANSIBLE
- Cycle de vie de TOUTE ressource (VLAN, pool, VM, LXC, routes Traefik, accès VPN,
  connexions Guacamole, règles firewall, services du catalogue, objets Entra ID,
  organisations/dashboards/règles d'alerte de monitoring) = OpenTofu + Ansible.
- InfraOne génère HCL/tfvars/config depuis des templates (Jinja), lance
  `tofu init/plan/apply` et les playbooks dans un JOB ASYNCHRONE (worker + file),
  capture la sortie, affiche statut et logs dans l'UI.
- API Proxmox DIRECTE uniquement pour les actions sans état (start/stop/reboot,
  statut).
- RÈGLE ANTI-DRIFT : une ressource = un seul propriétaire. Aucune config faite à la
  main dans une interface : tout part de Git.
- State : backend PostgreSQL, 1 WORKSPACE PAR CLIENT, state ET plans CHIFFRÉS.
- Providers : bpg/proxmox (Proxmox, y compris les boîtiers sur site),
  hashicorp/azuread (Entra ID), grafana/grafana (organisations, sources de données,
  dossiers, dashboards, utilisateurs), ovh (DNS si domaine OVH). OPNsense : via son
  API par Ansible (module uri) ; évaluer le provider communautaire
  browningluke/opnsense et documenter le choix.

Structure :
infra/ (providers, backend pg chiffré)
  modules/platform/        socle : réseaux/VLANs, VMs firewall, docker-dmz, presta,
                           supabase, monitoring
  modules/client/          1 tenant : VLAN + sous-réseau + pool + ACL + VPN
                           tunnel/site + VM runtime + identité + observabilité
  modules/instance/        1 VM ou LXC paramétrable (avec tag Proxmox tenant-<id>
                           et agent de monitoring)
  modules/site/            boîtier sur site (nœud Proxmox client) : DC2, FOG,
                           WireGuard, Grafana Alloy
  modules/entra/           baseline d'un tenant Entra (groupes, rôles, app, etc.)
  modules/observability-tenant/  org Grafana du client, datasources (via
                           prom-label-proxy et Loki tenant), dossiers, dashboards,
                           utilisateurs, routes d'alerte
  templates/               gabarits rendus par InfraOne
monitoring/
  dashboards/client/       modèles JSON des dashboards client (variables)
  dashboards/prestataire/  modèles JSON des dashboards prestataire
  dashboards/overrides/<client>/  dashboards spécifiques à un client
  rules/                   recording rules + règles d'alerte par défaut
  alertmanager/            gabarits de routage par tenant
ansible/roles/             base+hardening, docker, traefik, guacamole, opnsense,
                           samba-ad, fog, windows (WinRM/OpenSSH, winget, sysprep),
                           monitoring, node_exporter, windows_exporter, cadvisor,
                           alloy, 1 rôle PAR SERVICE du catalogue, outils presta

## 2. ARCHITECTURE & ZONES RÉSEAU
Proxmox VE : vmbr0 (WAN) / vmbr1 (LAN privé, VLAN-aware). OPNsense en VM =
firewall/passerelle de toutes les zones.

| Zone | VLAN | Sous-réseau | Contenu |
| MANAGEMENT | 99 | 10.0.99.0/24 | InfraOne (LXC), docker-mgmt (Portainer),
  monitoring, Supabase (données InfraOne + state tofu) |
| PRESTATAIRE | 60 | 10.0.60.0/24 | outils multi-clients : GLPI, MeshCentral,
  Vaultwarden presta, BookStack presta |
| DMZ / ACCÈS | 50 | 10.0.50.0/24 | Traefik (seule entrée HTTPS), Guacamole |
| CLIENT N | 10,20,30… | 10.0.<vlan>.0/24 | VM runtime Docker du client, DC1 Samba
  AD (VM) le cas échéant |
| TUNNELS VPN UTILISATEURS | — | 10.200.<vlan>.0/24 | accès VPN des utilisateurs
  du client N |
| SITES CLIENTS (LAN physiques) | — | 172.16.<n°client>.0/24 | réseau des locaux
  de la PME, RENUMÉROTÉ selon ce plan (sinon NAT 1:1 documenté) |
| VPN ADMIN | — | 10.250.0.0/24 | équipe prestataire → VLAN 99 et 60 |

- OVH : IP principale sur l'hôte. Par défaut tout passe par OPNsense → Traefik.
- VPN SITE-À-SITE par client : IPsec IKEv2 (routeur du client) ou WireGuard
  (boîtier InfraOne). Le tunnel du site N arrive UNIQUEMENT dans le VLAN du client N.
- PLAGES QUI SE CHEVAUCHENT : interdites dans une même table de routage (OPNsense
  n'a pas de VRF). Renumérotation 172.16.<n>.0/24 à l'arrivée du client ; NAT 1:1
  en secours.
- BOÎTIER SUR SITE (optionnel, clients à partir d'environ 10 postes) : mini-PC x86
  16 Go sous Proxmox VE, piloté par le même OpenTofu (module site) : DC2 Samba (VM),
  maître FOG (VM), point d'arrivée WireGuard, Grafana Alloy (monitoring local
  poussé vers le central).

Matrice des flux (deny par défaut ; uniquement ces autorisations, documentées) :
- Internet → WAN : 443/80 vers Traefik ; UDP WireGuard ; IPsec (UDP 500/4500) des
  sites clients déclarés. Rien d'autre.
- Traefik → portail InfraOne (port de l'app) ; Grafana (UNIQUEMENT avec forwardAuth
  InfraOne) ; services publiés des clients (port du service) ; endpoints AGENTS de
  GLPI et MeshCentral (VLAN 60).
- guacd → VLANs clients : 22/3389/5900.
- Site client N ↔ VLAN client N : ports AD (53, 88, 135 + plage RPC dynamique, 389,
  445, 464, 636, 3268/3269, 123), services du client.
- Boîtier du site N → VLAN 99 : UNIQUEMENT le port remote-write de Prometheus et le
  port d'ingestion Loki (via le VPN du site).
- Tunnel utilisateur du client N → VLAN N uniquement.
- VPN admin → VLAN 99 et 60. VLAN 60 → VLANs clients : uniquement les ports
  nécessaires aux outils presta.
- Prometheus (99) → ports des exporters dans toutes les zones. Les VLANs clients ne
  peuvent JAMAIS joindre Prometheus, Loki ou Alertmanager directement.
- INTERDIT : client ↔ client, client → 99/60, DMZ → 99 (sauf portail InfraOne et
  Grafana via forwardAuth), site N → autre VLAN.

## 3. ACCÈS DES CLIENTS À LEURS RESSOURCES (3 couches)
Identité : compte InfraOne par utilisateur, rattaché à un client, MFA OBLIGATOIRE.
Portail client public via Traefik. Fonctions d'admin et outils internes : VPN admin.
- Couche 1, Traefik (toujours) : `<service>.<client>.<domaine>`, certificat
  wildcard Let's Encrypt (DNS-01 OVH), routes générées par InfraOne (provider
  fichier), middlewares : en-têtes de sécurité, rate limit, IP allowlist
  optionnelle, bouncer CrowdSec.
- Couche 2, Guacamole (console par défaut, sans installation) : bouton « Ouvrir la
  console » ; extension officielle « Encrypted JSON authentication » (InfraOne signe
  la liste des connexions autorisées du client, pas de second login) ; connexions
  créées/supprimées par les jobs ; ENREGISTREMENT DES SESSIONS ; identifiants des
  VMs non affichés.
- Couche 3, WireGuard utilisateur (option, clients techniques) : tunnel
  10.200.<vlan>/24 → son VLAN ; config affichée UNE fois (QR/fichier), clé privée
  non conservée ; révocation, expiration, liste des pairs actifs.
Créer un client = UN job (VLAN, pool, VPN, règles, Guacamole, Traefik, VM runtime,
identité, OBSERVABILITÉ). Supprimer un client = tout révoquer, dans l'ordre inverse.

## 4. IDENTITÉ DES CLIENTS — 3 PROFILS, UN SEUL PAR CLIENT
Champ `identity_mode` dans la fiche client, JAMAIS deux annuaires pour un même client :
- `lldap` : client sans poste Windows. Annuaire léger (~30 Mo) dans sa VM runtime ;
  les services du catalogue s'y authentifient.
- `samba-ad` (CLASSIQUE) : postes Windows sur site. Samba AD DC EN VM (jamais en
  Docker), niveau fonctionnel 2008 R2 (2012 R2 peu testé, 2016 expérimental).
  2 DC en production : DC1 dans le VLAN client (OVH), DC2 sur le boîtier sur site.
  Pas de réplication DFS-R du SYSVOL : synchronisation à sens unique (rsync),
  modification des GPO sur un seul DC. Pas de mélange avec des DC Windows en
  2012 R2. GPO gérées via RSAT depuis un poste d'admin. Son LDAP sert aussi aux
  services. Option premium documentée : Windows Server AD DS (licences SPLA).
- `entra-id` (MODERNE) : 1 CLIENT = 1 TENANT ENTRA (cloisonnement natif). Postes
  joints à Entra + Intune + Autopilot, sans contrôleur de domaine.
  Hybride Samba AD + Entra Connect : NON supporté par Microsoft → hors périmètre,
  uniquement en R&D expérimentale documentée.

## 5. POSTES WINDOWS — DEUX PARCOURS DE DÉPLOIEMENT
Parcours CLASSIQUE (samba-ad) — images « masters » :
- FOG Project : le maître FOG est sur le BOÎTIER DU CLIENT (la capture et le
  multicast ne fonctionnent que depuis le maître). Bibliothèque centrale des
  masters dans Garage (S3) ; un job InfraOne pousse le bon master vers le FOG du site.
- Chaîne de fabrication d'un master (IaC, versionné) : VM « build » créée dans
  Proxmox par OpenTofu depuis l'ISO → Ansible (WinRM/OpenSSH) : mises à jour +
  logiciels via winget → Sysprep + unattend.xml → capture FOG → stockage versionné
  (`master-<client>-vN`) → déploiement PXE → jonction automatique au domaine Samba
  AD → finalisation Ansible / snapins.
- Image indépendante du matériel + pilotes injectés par modèle de PC.
- À TESTER sur le matériel réel : Secure Boot avec FOG (non confirmé,
  désactivation temporaire possible) ; activation des licences (KMS/MAK/OEM) et
  droits de réimaging.
- Écartés et documentés : MDT (retiré en janvier 2026), WDS (déprécié), SCCM (trop
  lourd). netboot.xyz/iPXE en complément (dépannage). Clonezilla SE en secours.
Parcours MODERNE (entra-id) — sans image :
- Windows Autopilot + Intune : InfraOne collecte l'empreinte matérielle du poste
  (script via MeshCentral ou Ansible) et l'importe via Microsoft Graph ; profil
  Autopilot + politiques Intune de base par client.

## 6. CATALOGUE DE SERVICES CLIENTS (packs)
Exécution : 1 VM « runtime » Docker PAR CLIENT dans son VLAN. Jamais deux clients
sur le même moteur Docker. Bases MUTUALISÉES par client : 1 PostgreSQL + 1 MariaDB
+ 1 Valkey (pas Redis, pour la licence). `mem_limit`/`cpus` sur CHAQUE conteneur,
images épinglées par digest, sauvegardes (dumps + volumes) vers le stockage
d'infra. 1 rôle Ansible + 1 template compose par service ; route Traefik générée.
Chaque conteneur porte les labels `infraone.tenant`, `infraone.service`,
`infraone.pack` (utilisés par le monitoring).
Packs (RAM approximative, à mesurer) :
- Socle (toujours, ~0,8 à 1 Go) : VM runtime + Postgres + MariaDB + Valkey +
  annuaire (lldap, ou LDAP du Samba AD) + cAdvisor + node_exporter.
- Essentiel (~0,3 Go) : Vaultwarden, Uptime Kuma, BookStack.
- Collaboration (~0,5 à 0,9 Go) : Nextcloud (+Valkey), WordPress (durci).
- Automatisation (~0,3 à 0,4 Go) : Activepieces (édition communautaire MIT).
  n8n est INTERDIT dans le catalogue client (licence Sustainable Use : pas
  d'hébergement facturé pour des tiers ; LDAP/SSO payants). n8n est autorisé en
  INTERNE pour le prestataire.
- Parc IT (~0,2 Go) : AdGuard Home. (GLPI et MeshCentral sont des outils
  prestataire multi-clients, voir section 7.)
- Stockage (~0,1 Go) : Garage (S3, AGPL). MinIO est INTERDIT (projet archivé, plus
  d'images ni de correctifs). Garage n'a pas d'Object Lock : les sauvegardes
  immuables relèvent de l'infra.
Exclus et documentés : serveur mail complet (délivrabilité), chat (Mattermost,
Rocket.Chat, Matrix), Odoo, Jitsi, Wazuh/ELK, Keycloak, Bitwarden officiel, FreeIPA.
Page « Catalogue » dans le portail : le client active ou désactive des packs → job
IaC (qui active aussi le monitoring du service, section 9).

## 7. OUTILS DU PRESTATAIRE (VLAN 60, UNE instance multi-clients chacun)
- GLPI : 1 ENTITÉ PAR CLIENT. GLPI Agent sur chaque poste avec un TAG par client et
  une règle d'affectation automatique à l'entité (procédure à valider selon la
  version). Inventaire, tickets, contrats ; portail client limité à son entité.
- MeshCentral : 1 groupe d'appareils par client ; prise en main à distance,
  terminal, fichiers ; MFA ; l'agent fonctionne hors VPN via Traefik (endpoint agent
  seulement).
- Vaultwarden prestataire (distinct de ceux des clients) : 1 organisation par client
  pour les identifiants d'administration.
- BookStack prestataire : 1 étagère par client (procédures, schémas, contacts).
- Patching : phase de base = Windows Update for Business par GPO (samba-ad) ou
  Intune (entra-id), rapports via GLPI/MeshCentral. Plus tard : Tactical RMM
  (licence non open source : usage prestataire OK, hébergement comme service
  interdit sans accord) ; NetBox (IPAM alimenté par InfraOne).
- n8n interne : automatisations du prestataire (onboarding, rapports, alertes).
RBAC InfraOne : Admin prestataire (tout, VPN admin) · Technicien (uniquement les
clients assignés explicitement, chaque accès journalisé) · Admin client ·
Utilisateur client. Procédure « bris de glace » documentée et auditée.

## 8. LABORATOIRE ENTRA ID (tests multi-tenant)
Objectif : démontrer le cloisonnement 1 client = 1 tenant et la gestion
centralisée par le prestataire.
- Tenants de test : 1 « Prestataire » + 2 ou 3 « Clients » (chaque membre de
  l'équipe peut porter un tenant). Licences de test : essai Intune 30 jours (EMS :
  Entra P1/P2 + Intune) ou essai Entra P1/P2 30 jours ; Microsoft 365 Developer
  Program si l'école fournit Visual Studio Pro/Enterprise. NE PAS utiliser l'essai
  Business Premium (carte bancaire + conversion automatique en abonnement payant).
  Caler les essais de 30 jours sur un sprint dédié. MFA obligatoire pour les admins.
- Ne JAMAIS travailler dans le tenant de l'école : créer des tenants dédiés.
- Gestion par le prestataire (sans statut partenaire CSP) : application InfraOne
  MULTI-TENANT enregistrée dans le tenant Prestataire. Lien de consentement admin
  généré par InfraOne pour chaque client. Jetons « client credentials » PAR TENANT
  (scope Graph .default). Authentification par CERTIFICAT (pas de secret si
  possible). Permissions de type APPLICATION, au minimum nécessaire. VALIDER le
  tenant ID renvoyé après consentement (risque de falsification). « Non vérifié »
  accepté en lab.
- Cible production documentée : GDAP via Partner Center (CSP), rôles granulaires,
  durée ≤ 2 ans, approbation par le client.
- IaC : workspace OpenTofu du client = son tenant (provider hashicorp/azuread) :
  groupes de base (Utilisateurs, Admins, Techniciens-prestataire), utilisateurs de
  test, rôles. Accès conditionnel (MFA) et baseline Intune via Microsoft Graph
  depuis InfraOne (évaluer la couverture des providers et documenter).
- Postes de test : VMs Windows 11 dans Proxmox (UEFI/OVMF, vTPM, Secure Boot),
  édition ÉVALUATION Enterprise 90 jours (pas l'édition Famille). Démonstration :
  Autopilot → jonction Entra → Intune → poste visible dans GLPI/MeshCentral.
- Démonstration du cloisonnement : prouver qu'un jeton ou un technicien du client A
  ne voit et ne modifie rien dans le tenant B (test automatisé).
- Sauvegarder les configurations des tenants (exports Graph) dans Git ; supprimer
  proprement les tenants et révoquer les consentements à la fin du projet.

## 9. OBSERVABILITÉ — MONITORING AUTOMATIQUE (PRESTATAIRE + CLIENTS)

### 9.1 Stack
VM monitoring (VLAN 99, 3 à 4 Go) : Prometheus (avec récepteur remote-write activé
pour les sites), Alertmanager, Grafana OSS, Loki en mode multi-tenant
(auth_enabled: true), blackbox_exporter, prom-label-proxy. Compose versionné,
déployé par Ansible. Rétention Prometheus 30 jours. Organisations, sources de
données, dossiers, dashboards, utilisateurs Grafana et routes d'alerte gérés par
OpenTofu (provider grafana/grafana, module observability-tenant) dans le workspace
de chaque client.

### 9.2 Principe : zéro action manuelle
Tout ce qu'InfraOne crée est supervisé automatiquement ; tout ce qu'il supprime
cesse de l'être.
- L'inventaire d'InfraOne est la SOURCE DE VÉRITÉ. InfraOne expose
  `GET /internal/sd/<job>` au format Prometheus HTTP SD (tableau JSON de
  `targets` + `labels`), protégé par jeton (en-tête Authorization), relu toutes les
  30 s. En cas d'erreur, Prometheus garde la dernière liste valide.
- Labels obligatoires sur chaque cible : tenant, resource_id, resource_kind
  (vm | lxc | docker | service | site | windows | dc), resource_name, service, pack.
- Jobs de découverte : node (Linux), windows, cadvisor, blackbox_http (URLs publiées,
  dérivées des routes Traefik), blackbox_tcp_dns (DC : LDAP/Kerberos/DNS), exporters
  applicatifs du catalogue (postgres, mysqld, redis…).

### 9.3 Trois niveaux de collecte, activés dès la création
- NIVEAU 0, sans agent, IMMÉDIAT : prometheus-pve-exporter fournit CPU, RAM,
  disque, réseau et état de chaque VM et LXC dès qu'elle existe (y compris
  Windows). Rattachement au client par RECORDING RULES : jointure des séries pve
  (label id="qemu/<vmid>" ou "lxc/<vmid>") avec une métrique d'information exposée
  par InfraOne `infraone_resource_info{id, tenant, resource_name, resource_kind}`
  → séries `infraone:guest_*` portant le label tenant. Ne PAS compter sur les tags
  Proxmox dans pve-exporter (non confirmé) ; OpenTofu pose quand même le tag
  Proxmox `tenant-<id>` sur chaque ressource (lisibilité dans l'UI Proxmox).
- NIVEAU 1, agent installé automatiquement : node_exporter (VM et LXC Linux, via
  cloud-init + rôle Ansible) ; windows_exporter (serveurs Windows, via Ansible
  WinRM/OpenSSH) ; DC Samba via node_exporter ; cAdvisor sur chaque VM runtime
  Docker avec `store_container_labels=false` et
  `whitelisted_container_labels=infraone.tenant,infraone.service,infraone.pack`.
- NIVEAU 2, applicatif : exporter du service quand il existe (tableau 9.6) + sonde
  blackbox HTTP/TLS générée automatiquement pour CHAQUE URL publiée + sondes
  TCP/DNS pour les DC.

### 9.4 Cycle de vie dans les jobs de provisionnement
- CRÉATION : tofu apply (tag Proxmox tenant) → cloud-init/Ansible installe l'agent
  → InfraOne enregistre la ressource dans son inventaire (avec labels) → la
  découverte l'expose → DERNIÈRE ÉTAPE DU JOB : vérifier sous 120 s que `up == 1`
  pour la cible et que les séries `infraone:guest_*` existent. Sinon, statut « succès
  avec avertissement : monitoring inactif » + alerte au prestataire.
- ARRÊT VOLONTAIRE (stop par l'utilisateur) : InfraOne crée un SILENCE Alertmanager
  ciblé sur la ressource ; au démarrage, il le supprime. Mode maintenance du client
  = silence planifié.
- ACTIVATION D'UN PACK : exporters et sondes du service ajoutés automatiquement.
- SUPPRESSION : retrait de l'inventaire → cible retirée de la découverte → aucune
  alerte fantôme ; les données restent jusqu'à la fin de la rétention.
- SITES DISTANTS (boîtier) : Grafana Alloy sur le boîtier collecte localement et
  pousse en remote_write vers Prometheus et Loki, avec le label tenant ajouté à la
  source (external_labels), via le VPN du site, sur ces seuls ports.

### 9.5 Isolation par client avec Grafana OSS
Le contrôle d'accès par label de Grafana (LBAC) est réservé aux éditions Enterprise
et Cloud : NE PAS l'utiliser. L'isolation est imposée EN AMONT :
- 1 ORGANISATION GRAFANA PAR CLIENT + 1 organisation « Prestataire ».
- La source Prometheus de l'organisation client pointe vers prom-label-proxy, qui
  IMPOSE `tenant="<client>"` dans chaque requête (lecture seule). Soit une
  instance de proxy par client, soit une instance unique avec le label fixé par un
  en-tête défini dans la source de données. L'authentification doit avoir lieu
  AVANT le proxy.
- La source Loki de l'organisation client envoie l'en-tête `X-Scope-OrgID=<client>`
  (Loki multi-tenant natif) ; Alloy pousse les logs de chaque client avec son tenant.
- Les clients n'ont PAS le droit de modifier les sources de données. Rôles :
  Viewer sur les dashboards provisionnés (en lecture seule, gérés par l'IaC) ;
  Editor uniquement sur un dossier « Mes dashboards » pour leurs créations.
- Alertes du client : lues via le backend InfraOne (filtre tenant côté serveur),
  jamais d'accès direct à Alertmanager.
- Connexion à Grafana :
  Phase 1 : Grafana en auth.proxy derrière Traefik avec forwardAuth vers InfraOne
  (session + MFA), qui renvoie l'en-tête utilisateur ; utilisateurs pré-provisionnés
  dans leur organisation par OpenTofu. Traefik SUPPRIME tout en-tête X-WEBAUTH-*
  entrant ; Grafana n'accepte ces en-têtes que depuis l'IP de Traefik et n'est
  joignable par aucun autre chemin.
  Phase 4 : Authentik + generic OAuth avec association aux organisations (Grafana
  ≥ 11.2, org_attribute_path).
- TESTS AUTOMATISÉS ANTI-FUITE : un utilisateur du client A essaie `tenant="B"`,
  des regex, `{__name__=~".+"}`, l'Explorateur, Loki, les liens profonds avec
  l'identifiant d'organisation de B → aucune donnée de B ne doit être renvoyée.

### 9.6 Collecteurs (ports INTERNES, scrapés depuis le VLAN 99)
| Proxmox (API) | prometheus-pve-exporter, token PVEAuditor (privsep : ACL du
  token) | 9221 |
| VMs, LXC, hôtes, boîtiers | node_exporter (+ smartctl_exporter sur le bare
  metal) | 9100 |
| Serveurs Windows | windows_exporter | 9182 |
| OPNsense | os-node_exporter (9100) + opnsense-exporter (API lecture seule ;
  métriques WireGuard/IPsec selon l'exporter, à vérifier) | 8080 |
| Traefik | métriques natives, entrypoint dédié réservé au VLAN 99 | 8082 |
| Conteneurs Docker | cAdvisor (labels infraone.*) | 8080 |
| Postgres / MariaDB / Valkey | postgres_exporter / mysqld_exporter /
  redis_exporter | 9187/9104/9121 |
| Supabase | PostgREST /metrics (admin, 3001), plugin prometheus de Kong ;
  GoTrue : à vérifier | — |
| Garage | métriques natives sur l'API admin (à vérifier selon la version) | 3903 |
| n8n interne | /metrics natif (N8N_METRICS=true) | 5678 |
| Uptime Kuma | /metrics (Basic Auth + clé API) | interne |
| Samba AD, FOG, Portainer, Guacamole, Vaultwarden, BookStack, GLPI, MeshCentral,
  Activepieces, WordPress | pas de métriques natives (ou à vérifier) :
  node_exporter + cAdvisor + blackbox + logs | — |
| URLs publiques + certificats | blackbox_exporter | 9115 |
| InfraOne | prometheus-fastapi-instrumentator + métriques métier : jobs (statut,
  tenant, durée), file, échecs tofu, échecs de login, sessions console, pairs VPN,
  tunnels de sites, services actifs par client, `infraone_resource_info` | interne |

### 9.7 Dashboards (provisionnés en code, à variables, mis à jour par job)
Modèles JSON versionnés dans `monitoring/dashboards/`, sources de données
référencées par variable, déployés par OpenTofu dans chaque organisation. Une
évolution d'un modèle est appliquée à TOUS les clients par un job. AUCUN dashboard
par VM : des dashboards à VARIABLES ($resource, $service, $container), où toute
nouvelle ressource apparaît automatiquement. Liens profonds depuis InfraOne
(`?orgId=<org>&var-resource=<id>`).
Organisation CLIENT :
1. Vue d'ensemble : santé globale, ressources par type et état, alertes actives,
   plus gros consommateurs, consommation par rapport au pack, disponibilité 30 j.
2. Machines virtuelles ($vm) : CPU, RAM, disque (occupation + I/O), réseau,
   uptime, load, systèmes de fichiers, état de l'agent (niveau 0 seul ou niveau 1).
3. Conteneurs LXC ($lxc) : même structure, adaptée.
4. Conteneurs Docker & services ($service, $container) : CPU, RAM comparée à
   mem_limit, redémarrages, arrêts OOM, réseau, santé blackbox du service.
5. Bases de données : Postgres, MariaDB, Valkey du client (connexions, requêtes,
   cache, taille).
6. Disponibilité & SLA : par URL publiée : uptime %, latence, codes HTTP,
   expiration TLS ; SLA du mois en cours.
7. Serveurs Windows & annuaire : windows_exporter ; DC : joignabilité
   LDAP/Kerberos/DNS, statut de la synchro SYSVOL.
8. Réseau & sites : tunnels VPN du site, latence, trafic du VLAN du client
   (métriques d'interface OPNsense rattachées au tenant par recording rule).
9. Logs : exploration Loki du tenant, erreurs par service.
Organisation PRESTATAIRE :
A. Flotte multi-clients : état de tous les clients, alertes par client.
B. Capacité & planification : RAM/CPU/disque engagés vs physiques (OVH +
   boîtiers), surallocation, projection.
C. Consommation par client = BASE DE FACTURATION (vCPU·h, Go RAM·h, stockage,
   trafic).
D. Socle infra : Proxmox, OPNsense, Traefik, Postgres, InfraOne (jobs), sécurité
   (échecs d'auth, CrowdSec, Suricata, certificats, VPN).
E. Santé du monitoring : cibles en panne, durées de scrape, cardinalité par client.
Dashboards communautaires réutilisables comme base (vérifier la compatibilité de
version) : 1860, 10347, 14282, 9628, 21113, Traefik 17346, Blackbox.
Dashboards spécifiques à un client : `monitoring/dashboards/overrides/<client>/`,
appliqués par l'IaC.

### 9.8 Alertes automatiques par client
- Règles PAR DÉFAUT appliquées à toute ressource dès sa création (labels tenant et
  resource) : ressource injoignable, CPU > 90 % pendant 15 min, RAM > 90 %, disque
  > 85 % et prévision « plein sous 24 h » (predict_linear), conteneur qui redémarre
  en boucle, arrêt OOM, service HTTP en panne, latence élevée, certificat < 14 jours,
  sauvegarde manquante, tunnel de site en panne, DC injoignable.
- Seuils PERSONNALISABLES par client et par ressource dans InfraOne → génération
  des fichiers de règles par tenant.
- Routage Alertmanager par label tenant → contacts du client (email) + prestataire
  (toujours) ; configuration générée par job à partir de la fiche client ;
  sévérités warning/critical ; regroupement ; INHIBITION (une VM en panne masque les
  alertes de ses services).
- Silences automatiques (arrêt volontaire, maintenance).
- Alertes visibles dans le portail client (filtrées côté backend). Phase 2 : ticket
  GLPI ouvert automatiquement dans l'entité du client pour les alertes critiques.
- Alertes du socle (prestataire uniquement) : cibles du socle DOWN, échec de job
  tofu, file de jobs bloquée, pics d'échecs de login, CrowdSec/Suricata, 5xx
  Traefik, réplication SYSVOL en échec, Postgres injoignable, jeton/consentement
  Entra expiré, cardinalité anormale d'un client.

### 9.9 Intégration dans InfraOne
- Page de chaque machine et conteneur : mini-graphes 24 h (CPU, RAM, disque,
  réseau) via l'API Prometheus CÔTÉ BACKEND avec le tenant imposé par le serveur,
  statut du monitoring (agent OK / niveau 0 seulement / inactif), alertes actives,
  bouton « Ouvrir dans Grafana » (lien profond).
- Page Monitoring du portail client : ses dashboards, alertes, SLA, logs, réglage
  des seuils et des contacts d'alerte.
- Phase 2 : RAPPORT MENSUEL PDF par client généré par InfraOne (disponibilité,
  incidents, consommation), car la fonction de rapports de Grafana est payante.
  Historique des SLA mensuels conservé dans Postgres (au-delà de la rétention
  Prometheus).

### 9.10 Maîtrise de la charge
Scrape à 30 s (60 s pour pve-exporter), `sample_limit` et `label_limit` par job,
metric_relabel pour supprimer les séries inutiles (cAdvisor : docker_only,
métriques non utilisées désactivées), cardinalité suivie par client (dashboard E).
Ordre de grandeur à mesurer : 1 à 2 Go de RAM pour Prometheus avec environ 30
machines et 100 conteneurs. Phase 4 : stockage long terme multi-tenant natif
(Grafana Mimir ou VictoriaMetrics cluster) si la volumétrie l'exige.

### 9.11 Logs
Grafana ALLOY (PAS Promtail, en fin de vie depuis le 02/03/2026) vers Loki
multi-tenant : journald, OPNsense (filterlog, Suricata, IPsec/WireGuard), Traefik
(JSON), Guacamole, Samba (auth), FOG, audit InfraOne, jobs tofu/ansible, conteneurs
Docker des clients (labels tenant/service), journaux Entra (connexions/audit via
Graph, licence P1 requise pour les connexions) collectés par un job InfraOne.

### 9.12 Critères d'acceptation
- Créer une VM, un LXC et un conteneur (en mock ET en réel) : visibles dans les
  dashboards DU BON CLIENT en moins de 2 minutes, sans aucune action manuelle.
- Les supprimer : ils disparaissent de la supervision sans alerte fantôme.
- Arrêt volontaire : aucune alerte envoyée.
- Tests anti-fuite (9.5) réussis.
- Une alerte de test atteint le bon client uniquement (et le prestataire).
- Toutes les cibles du socle UP, dashboards sans panneau vide.

## 10. SÉCURITÉ — NIVEAU ÉLEVÉ, DÉFENSE EN PROFONDEUR (OWASP ASVS niveau 2 pour l'app)
- Périmètre : firewall réseau OVH + anti-DDoS ; seuls ouverts : 80/443 Traefik,
  WireGuard, IPsec des sites déclarés. Proxmox firewall en 2e couche. OPNsense : deny
  par défaut, matrice des flux, Suricata sur le WAN, CrowdSec. Interfaces d'admin
  (Proxmox, OPNsense, Portainer, organisation Prestataire de Grafana, Prometheus,
  Alertmanager, Studio, dashboard Traefik, admin Guacamole, GLPI admin, MeshCentral
  admin, admin InfraOne) : VPN ADMIN UNIQUEMENT.
- Identités : MFA partout (Proxmox, OPNsense, Grafana via InfraOne, InfraOne, GLPI,
  MeshCentral, admins Entra). Phase ultérieure : Authentik (SSO + forward-auth).
  Moindre privilège : tokens Proxmox séparés (OpenTofu / InfraOne live /
  pve-exporter) ; clé API OPNsense dédiée ; jeton dédié pour la découverte HTTP SD ;
  compte de service Grafana dédié à OpenTofu ; permissions Graph minimales par
  tenant ; aucun compte partagé ; SSH par clé.
- Monitoring : exporters jamais joignables depuis les VLANs clients ni Internet ;
  isolation des métriques par prom-label-proxy et des logs par tenant Loki ;
  protection de l'auth.proxy Grafana (en-têtes supprimés par Traefik, IP source
  vérifiée) ; tests anti-fuite dans la CI.
- Active Directory : ports jamais publics ; comptes Admins du domaine séparés et
  utilisés uniquement sur les DC et un poste d'admin ; mots de passe admin locaux
  uniques par poste (LAPS : compatibilité Samba à valider) ; GPO de durcissement.
- Secrets : jamais dans Git ; SOPS + age (ou Ansible Vault) ; state ET plans tofu
  chiffrés (aes_gcm + pbkdf2, passphrase en env, test avec le backend pg) ; Postgres
  en TLS ; certificats de l'app Entra, secret JSON Guacamole et jetons de
  monitoring stockés comme secrets, avec rotation.
- Durcissement : devsec.hardening, unattended-upgrades, agent CrowdSec ; Docker
  non-privileged, non-root, no-new-privileges, read-only quand c'est possible,
  digest, Trivy ; docker.sock jamais exposé (docker-socket-proxy en lecture seule).
- Application : JWT court + refresh, cookies sécurisés, rate limit + verrouillage,
  CORS restreint, CSP/HSTS, pydantic strict, multi-tenant (tenant_id, RBAC, RLS)
  avec TESTS anti-IDOR (y compris pour les techniciens non assignés et les
  mini-graphes de monitoring). Worker : jamais shell=True, variables validées par
  schéma, utilisateur dédié, timeouts. Jeton de reset envoyé par email uniquement.
  AUDIT LOG de toute action (accès technicien, console, VPN, consentement Entra,
  modification de seuils d'alerte) vers Loki.
- Sauvegardes 3-2-1 : vzdump/PBS hors site, Postgres, MariaDB, state tofu chiffré,
  config OPNsense, DC Samba (+ SYSVOL), masters FOG, exports des tenants Entra,
  configuration Grafana (déjà en IaC). Restauration TESTÉE. Alerte si un backup
  manque.
- CI/CD (GitLab CI) : tofu fmt/validate, tflint, trivy config, ansible-lint, bandit,
  pip-audit, gitleaks, trivy image, promtool check rules, validation JSON des
  dashboards ; revue du plan avant tout apply du socle.

## 11. INTERFACE — UI SOMBRE ET MODERNE
Palette sombre, accents, cards arrondies, typo soignée, pastilles de statut,
graphes ; responsive ; hors-ligne (aucun CDN obligatoire). Techno au choix
(Tailwind servi par FastAPI, ou React+Vite+Tailwind+shadcn) : décider et justifier.
- Espace PRESTATAIRE (VPN admin) : Dashboard · Clients (fiche : identity_mode, site,
  boîtier, packs, tenant Entra, contacts d'alerte) · Machines · Jobs/Provisionnement
  · Catalogue · Postes Windows (domaine, masters, FOG, Autopilot) · Réseau &
  Firewall (VLANs, tunnels de sites) · Reverse proxy · Accès clients · Outils presta
  (liens GLPI, MeshCentral…) · Monitoring (flotte, capacité, consommation, santé du
  monitoring) · Sécurité · Logs · Paramètres.
- Portail CLIENT (public, MFA) : Mes machines (avec mini-graphes et statut de
  monitoring) · Ouvrir la console · Mes services · Catalogue (activer des packs) ·
  Monitoring (dashboards, alertes, SLA, seuils, contacts) · Accès VPN · Mes tickets
  (GLPI) · Activité.
- Module Jobs central (file, temps réel, logs, plan avant apply, étape finale
  « monitoring vérifié »).
- Mode mock complet : faux runner tofu, FAUSSES MÉTRIQUES (petit exporter
  synthétique par ressource mock, pour que les dashboards et mini-graphes
  fonctionnent sans infra), fausse console, faux VPN, faux tenant Entra, faux FOG.

## 12. DOCUMENTATION (livrable obligatoire)
README.md · docs/ARCHITECTURE.md (zones, VLANs, adressage dont sites 172.16, matrice
des flux, schémas) · docs/IaC.md · docs/ACCES-CLIENT.md · docs/IDENTITE.md ·
docs/POSTES-WINDOWS.md · docs/CATALOGUE.md · docs/PRESTATAIRE.md · docs/LAB-ENTRA.md
· docs/MONITORING.md (architecture, découverte automatique, 3 niveaux de collecte,
cycle de vie, isolation par client, exporters/ports, alertes, charge, limites) ·
docs/DASHBOARDS.md (catalogue des dashboards client et prestataire, variables,
procédure pour en ajouter ou en personnaliser un) · docs/SECURITY.md (STRIDE
simplifié, matrice d'accès, incident, sauvegarde/restauration) · docs/INSTALLATION.md
(runbook OVH + boîtier sur site) · docs/MULTI-TENANT.md · docs/UI.md · mise à jour de
docs/METHODOLOGIE.md (nouvelles US par phase).

## 13. QUALITÉ & LIVRAISON
Python comme base, code commenté en français ; HCL et rôles idempotents ; tests de
fumée en mock : création complète d'un client (chaque identity_mode), job simulé,
anti-IDOR (client et technicien), révocation VPN, activation d'un pack,
cloisonnement Entra (mock), ENRÔLEMENT AUTOMATIQUE au monitoring (création →
cible visible avec le bon tenant ; suppression → cible retirée), silence
automatique à l'arrêt, ANTI-FUITE des métriques et des logs entre clients.
Commits clairs, une branche `feat/US-xxx-<slug>` par carte créée depuis `GPE-ETNA-V2`
(dépôt git ETNA), fusionnée dans `GPE-ETNA-V2` uniquement avec l'accord explicite de
l'équipe. Pas de push forcé.

## 14. DIMENSIONNEMENT & PHASES
Serveur OVH 32 Go NVMe (3 à 5 clients Windows avec DC1 chez OVH ; prévoir 64 Go
au-delà). VM monitoring : 3 à 4 Go. Boîtier sur site : mini-PC x86 16 Go.
- PHASE 1 (socle) : IaC + worker de jobs, zones et firewall, Traefik, Guacamole,
  WireGuard utilisateur, sécurité, UI sombre (espaces prestataire et client),
  catalogue Socle + Essentiel avec lldap, mode mock complet. MONITORING : 9.1 à 9.5,
  collecte niveaux 0/1/2, dashboards client 1 à 6 et prestataire A, B, D, E,
  alertes par défaut + routage par client + silences, mini-graphes dans InfraOne.
- PHASE 2 (prestataire & Windows) : VPN site-à-site, Samba AD (DC1), zone presta
  (GLPI entités, MeshCentral, Vaultwarden presta, BookStack presta), catalogue
  complet, LAB ENTRA ID (sprint dédié, calé sur les essais de 30 jours).
  MONITORING : dashboards 7 et 8, dashboard C (facturation), seuils personnalisables,
  tickets GLPI automatiques, rapport mensuel PDF.
- PHASE 3 (déploiement & sites) : boîtier sur site (module site), DC2, FOG + chaîne
  de masters, Autopilot via Graph. MONITORING : Alloy sur les boîtiers en
  remote_write.
- PHASE 4 (documenter seulement) : Authentik (et connexion OAuth à Grafana avec
  association aux organisations), NetBird, Tactical RMM, NetBox, GDAP/CSP, R&D
  hybride Samba + Entra Connect, stockage long terme des métriques (Mimir ou
  VictoriaMetrics cluster).

## ORDRE DE TRAVAIL
1) Lire le dépôt. 2) PHASE 1 complète et testée en mock. 3) PHASE 2. 4) PHASE 3.
5) Documentation à jour à chaque phase. 6) Commits réguliers.
