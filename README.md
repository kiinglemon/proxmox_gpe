# InfraOne — Console d'automatisation Proxmox (MVP TIC-GPE5)

> **Projet INFRA One** — Astrid • Edry • Yanis • Glodi • Randy
>
> InfraOne est une couche web d'automatisation **au-dessus de Proxmox** : elle
> permet à un administrateur système junior de **déployer et configurer des VM
> Linux depuis une interface web**, sans manipuler directement l'interface
> Proxmox ni le terminal.

Ce dépôt contient l'application MVP **et un script d'installation automatique**
qui met tout en place sur un hôte Proxmox neuf, en **une seule commande**.

---

## 🚀 Installation en une commande

Sur votre **hôte Proxmox neuf** (Debian/Proxmox VE), en root :

```bash
git clone <url-du-depot> proxmox_gpe
cd proxmox_gpe
sudo ./install.sh
```

Le script (`setup/bootstrap.sh`) exécute automatiquement, de façon **idempotente** :

| Étape | Script | Ce qu'elle fait |
|------|--------|-----------------|
| 00 | `00-preflight.sh`   | Détecte Proxmox, mesure RAM/CPU, **calibre les valeurs pour votre hôte 10 Go / 4 vCPU** |
| 10 | `10-host-packages.sh` | Installe Python, venv, Ansible, git, curl… |
| 20 | `20-proxmox-apiuser.sh` | Crée le rôle, l'utilisateur et le **token API** `infraone@pve!automation` |
| 30 | `30-vm-template.sh` | Télécharge l'image cloud **Debian 12** et crée un **template cloud-init** (id 9000) |
| 40 | `40-deploy-app.sh`  | venv + dépendances, clé JWT, **service systemd** `infraone`, démarrage |

À la fin, l'URL, l'identifiant et le mot de passe généré s'affichent :

```
✔ InfraOne est déployé.
   URL        : http://<ip-hote>:8000/
   Login      : admin
   Mot de passe : <généré, noté dans config/infraone.env>
```

### Variantes d'installation

```bash
sudo ./install.sh --mock         # mode DÉMO : app simulée, sans infra Proxmox
sudo ./install.sh --no-template  # ne crée pas le template (déjà présent)
sudo ./install.sh --no-apiuser   # ne recrée pas le token API
```

> **Adaptation 10 Go / 4 vCPU** : sur un hôte de moins de 12 Go, le préflight
> réduit automatiquement les limites (1 vCPU / 1024 Mo / 8 Go par défaut,
> max 2 vCPU / 2048 Mo / 20 Go) pour préserver l'hôte + InfraOne.

---

## 🧪 Mode démo (sans infrastructure)

Vos rétrospectives de sprint 1 et 2 pointaient un blocage récurrent :
*« aucune VM ni environnement Proxmox disponible »*. InfraOne intègre donc un
**mode mock** qui simule Proxmox — vous pouvez démontrer le login, la création
de VM, les logs et le déploiement de service **sans aucune infra**.

Sur un poste de dev (Linux/Mac, sans Proxmox) :

```bash
./scripts_dev_run.sh          # crée le venv, active le mock, lance sur http://localhost:8000
```

---

## 🗺️ Couverture des User Stories du MVP

| US | Fonctionnalité | Où |
|----|----------------|-----|
| **US-001** | Connexion (JWT) | `routers/auth.py` + écran login |
| **US-002** | Mot de passe oublié / réinitialisation | `routers/auth.py` |
| **US-003** | Créer une VM Linux (template, CPU/RAM/disque) | `routers/vms.py` + `proxmox_client.py` |
| **US-004** | Modifier la config d'une VM | `PUT /api/vms/{id}` |
| **US-005** | Tester la connexion SSH | `ssh_check.py` |
| **US-006** | Consulter les logs d'erreur formalisés | `logbook.py` + `routers/logs.py` |
| **US-007** | Déployer un service (Nginx/Apache) via Ansible | `ansible_runner.py` + `ansible/playbooks/` |

---

## 🏗️ Architecture

```
Navigateur ──► UI web légère (backend/app/web/index.html)
                     │  fetch /api/*  (JWT Bearer)
                     ▼
              FastAPI (backend/app)
              ├─ auth (JWT + bcrypt)
              ├─ proxmox_client ──► API REST Proxmox (proxmoxer)   ← clone template cloud-init
              ├─ ssh_check       ──► paramiko (test SSH)
              ├─ ansible_runner  ──► ansible-playbook (services)
              └─ logbook         ──► journal JSONL formalisé
```

- **Backend** : Python / **FastAPI** (conforme au stack de l'équipe).
- **Frontend MVP** : interface web autonome servie par FastAPI (zéro build Node,
  robuste sur petit hôte). Le vrai frontend React/Tailwind de l'équipe peut la
  remplacer plus tard (voir `docs/METHODOLOGIE.md`).
- **Infra** : Proxmox VE + template cloud-init + Ansible.

---

## ⚙️ Configuration

Toute la configuration vit dans `config/infraone.env` (généré par le bootstrap
à partir de `config/infraone.env.example`). Ce fichier **n'est pas versionné**
(il contient le secret du token). Voir l'exemple pour la liste complète.

Après modification :

```bash
sudo systemctl restart infraone
```

---

## 🔧 Commandes utiles

```bash
systemctl status infraone            # état du service
journalctl -u infraone -f            # logs en direct
curl http://localhost:8000/api/health
```

Lancement manuel (sans systemd) :

```bash
cd backend && source .venv/bin/activate
set -a; source ../config/infraone.env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Documentation API interactive : `http://<hote>:8000/docs`

---

## 📚 Documentation

- [`docs/METHODOLOGIE.md`](docs/METHODOLOGIE.md) — synthèse de la méthodologie
  Agile (Scrum + Kanban), rôles, story mapping, backlog et sprints.

---

## 🔐 Sécurité — à faire avant la production

Le MVP privilégie la démontrabilité. Avant tout usage réel :

- Changer `INFRAONE_ADMIN_PASSWORD` et régénérer `INFRAONE_SECRET_KEY`.
- Le jeton de réinitialisation est renvoyé dans la réponse **à des fins de démo**
  (US-002) ; en production, l'envoyer par email et ne pas le retourner.
- Restreindre le CORS (`allow_origins`) et activer TLS (reverse proxy).
- Vérifier le certificat Proxmox (`PROXMOX_VERIFY_SSL=true`) une fois un
  certificat valide en place.
