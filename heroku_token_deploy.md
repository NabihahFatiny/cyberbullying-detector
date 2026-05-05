# Heroku Deployment with API Token

## Step 1: Get Your API Token
1. Go to https://dashboard.heroku.com
2. Login with your verification code
3. Account Settings → API Key
4. Click "Create Authorization Token"
5. Give it a name like "cyberbullying-deploy"
6. Copy the token (starts with hr1...)

## Step 2: Use Token to Deploy
Once you have the token, run:
```bash
heroku config:set HEROKU_API_KEY=your-token-here
```

## Step 3: Deploy
```bash
heroku create cyberbullying-detector
git push heroku main
```

## Alternative: Just Use Railway.app (Recommended)
If MFA is too complicated, Railway.app is much easier:
- GitHub login
- No API tokens needed
- Free tier
- Auto-deploys from GitHub
