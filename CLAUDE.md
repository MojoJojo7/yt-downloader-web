# YT-Downloader-Web

Downloader YouTube accessible via navigateur web. Connu sous le nom **Kimeloader**.

## URLs
- Production : https://kimeloader.up.railway.app
- GitHub : https://github.com/MojoJojo7/yt-downloader-web

## Stack
- Backend : Python / Flask
- Frontend : HTML/CSS/JS vanilla, dark theme Apple (#0d0d0d, accent #ff3b30)
- Download engine : yt-dlp + ffmpeg
- Déploiement : Railway (plan gratuit, crédit 5$/mois)

## Architecture
- `app.py` : serveur Flask, routes, logique yt-dlp
- `templates/index.html` : UI complète
- Jobs en mémoire (dict) + JOBS_LOCK threading — pas de base de données
- Fichiers temporaires supprimés après envoi au client
- SSE (Server-Sent Events) pour le streaming de progression en temps réel

## Fonctionnalités
- Qualité vidéo : Best (4K+) / 1080p / 720p / 480p / 360p
- Format : MP4 / WebM / MKV
- Audio Only MP3 avec choix du bitrate : 128 / 192 / 320 kbps
- Support playlists YouTube
- Tooltip sur "Best" : "Highest available quality (4K+)"
- "Best" = pas de cap, prend la meilleure qualité dispo sur YouTube

## Lancer en local
```bash
pip3 install -r requirements.txt
python3 app.py
```
Puis ouvrir http://localhost:5000

Le serveur de dev est aussi configuré dans `.claude/launch.json` (dossier parent).

## Déploiement Railway
- Push sur `main` → déploiement automatique
- ffmpeg installé via `nixpacks.toml`
- Gunicorn avec timeout 300s (nécessaire pour les longs téléchargements)
- Variables d'environnement : aucune requise

## Règles
- Ne jamais committer sur main directement
- Format commits : type(scope): description en français
- Tester en local avant de pusher

## 🐛 Bugs connus — à régler prochaine session

### [2026-03-23] Unknown server error sur vidéos longues/4K
- **Reproduction** : vidéo 4K de 37 min → `[error] Unknown server error.`
- **Cause probable** : timeout Railway (300s) dépassé, ou mémoire insuffisante pour merger bestvideo+bestaudio en 4K
- **Pistes** :
  - Augmenter le timeout Gunicorn (déjà à 300s, peut-être insuffisant)
  - Streamer la sortie yt-dlp directement vers le client sans buffer complet en mémoire
  - Limiter "Best" à 1080p sur Railway et réserver 4K pour un usage local
  - Vérifier les logs Railway au moment de l'erreur

*Mis à jour : 2026-03-23*
