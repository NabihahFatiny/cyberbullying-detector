# Railway.app Deployment (Easier Alternative)

## Why Railway?
- No MFA login issues
- GitHub integration
- Free tier available
- Better for beginners

## Steps:

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub (easiest)

2. **Connect Your GitHub**
   - Click "New Project"
   - "Deploy from GitHub repo"
   - Select your cyberbullying repo

3. **Configure Environment**
   - Railway will detect Python automatically
   - Add these environment variables:
     - `PYTHON_VERSION`: `3.9`
     - `PORT`: `5000`

4. **Deploy**
   - Click "Deploy Now"
   - Railway will build and deploy automatically

## Files Already Ready:
✅ requirements.txt
✅ app.py (Flask app)
✅ Procfile (Railway will use this)

## Your App URL:
After deployment, Railway gives you a URL like:
https://your-app-name.railway.app
