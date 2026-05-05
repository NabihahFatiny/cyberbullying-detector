# Heroku Deployment Guide

## Prerequisites
- Heroku account (free)
- Heroku CLI installed
- Git initialized

## Steps

1. **Login to Heroku**
```bash
heroku login
```

2. **Create Heroku App**
```bash
heroku create your-app-name
```

3. **Push to Heroku**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

4. **Open App**
```bash
heroku open
```

## Files Already Ready:
✅ Procfile (configured for gunicorn)
✅ requirements.txt (all dependencies)
✅ Flask app structure

## Notes:
- Free tier has sleep time (activates on request)
- ML models load quickly enough for demo
- Data files are included in repo
