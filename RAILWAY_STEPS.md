# 🚀 Railway.app Deployment - Step by Step

## 📋 What You Need:
✅ GitHub account  
✅ Your code is committed to git  
✅ Railway account (free)

## 🎯 Step 1: Create GitHub Repository
```bash
# Go to GitHub.com → New repository → "cyberbullying-detector"
# Then run these commands:
git remote add origin https://github.com/YOUR_USERNAME/cyberbullying-detector.git
git branch -M main
git push -u origin main
```

## 🎯 Step 2: Deploy to Railway
1. **Go to**: https://railway.app
2. **Sign up** with GitHub (click "Continue with GitHub")
3. **Click**: "New Project" 
4. **Select**: "Deploy from GitHub repo"
5. **Choose**: your "cyberbullying-detector" repo
6. **Click**: "Deploy Now"

## 🎯 Step 3: Configure (Automatic)
Railway will automatically:
- Detect Python app
- Install requirements.txt
- Use Procfile to start with gunicorn
- Use railway.toml for configuration

## 🎯 Step 4: Get Your URL!
After 2-3 minutes, Railway gives you:
🌐 **Live URL**: `https://cyberbullying-detector.up.railway.app`

## ✅ Files Ready:
- `app.py` - Flask app
- `requirements.txt` - Dependencies  
- `Procfile` - Start command
- `railway.toml` - Railway config
- All data files included

## 🎉 That's it! Your cyberbullying detector is LIVE!

## 💡 Free Tier Benefits:
- $5 credit/month (plenty for this app)
- No sleep time (always instant)
- Custom domain support
- Automatic SSL
