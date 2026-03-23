# YT-Downloader-Web

Downloader YouTube accessible via navigateur web.

## Stack
- Backend : Python / Flask
- Frontend : HTML/CSS/JS vanilla
- Download engine : yt-dlp + ffmpeg
- Déploiement : Railway

## Architecture
- `app.py` : serveur Flask, routes, logique yt-dlp
- `templates/index.html` : UI complète (dark theme Apple)
- Jobs en mémoire (dict) — pas de base de données
- Fichiers temporaires supprimés après envoi au client

## Lancer en local
```bash
pip install -r requirements.txt
python app.py
```
Puis ouvrir http://localhost:5000

## Déploiement Railway
Push sur main → déploiement automatique.
Variables d'environnement : aucune requise.

## Règles
- Ne jamais committer sur main directement
- Format commits : type(scope): description en français
