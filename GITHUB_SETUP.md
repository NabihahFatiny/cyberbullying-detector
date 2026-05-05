# 🐙 GitHub Setup Steps

## 🎯 Step 1: Create GitHub Account (if you don't have one)
1. Go to https://github.com
2. Click "Sign up"
3. Choose free plan
4. Verify your email

## 🎯 Step 2: Create New Repository
1. Go to https://github.com/new
2. Repository name: `cyberbullying-detector`
3. Description: `AI-powered cyberbullying detection system`
4. Make it **Public** (free)
5. **Don't** add README, .gitignore, or license (we already have them)
6. Click "Create repository"

## 🎯 Step 3: Get Your Repository URL
After creating, GitHub will show you:
```
https://github.com/YOUR_USERNAME/cyberbullying-detector.git
```
Copy this URL!

## 🎯 Step 4: Push Your Code
Replace YOUR_USERNAME with your actual GitHub username:
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/cyberbullying-detector.git
git push -u origin main
```

## 🎯 Step 5: Deploy to Railway
1. Go to https://railway.app
2. Sign up with GitHub
3. New Project → Deploy from GitHub
4. Select your cyberbullying-detector repo
5. Deploy Now! 🚀
