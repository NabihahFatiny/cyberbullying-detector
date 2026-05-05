# 🚀 Vercel Deployment Guide - Step by Step

## 🎯 Goal: Deploy Your Cyberbullying Detector to Vercel

### Step 1: Go to Vercel
1. Open browser: https://vercel.com
2. Click "Sign Up" (top right)
3. Choose "Continue with GitHub"
4. Authorize Vercel to access your GitHub

### Step 2: Import Your Repository
1. After connecting to GitHub, click "New Project"
2. Click "Import Git Repository"
3. Search for: `cyberbullying-detector`
4. Select your repository (NabihahFatiny/cyberbullying-detector)
5. Click "Import"

### Step 3: Configure Deployment
Vercel will show this screen:
```
Framework Preset: Python
Root Directory: ./
Build Command: pip install -r requirements.txt
Output Directory: ./
Install Command: python app.py
```
✅ **Leave all settings as default** - they're correct!

### Step 4: Deploy
1. Click "Deploy" button
2. Wait for deployment (1-2 minutes)
3. You'll see: "Production: https://cyberbullying-detector.vercel.app"

### Step 5: Test Your App
1. Click the provided URL
2. Test with: "you stupid" → Should show "Cyberbullying Detected"
3. Test with: "why u cute" → Should show "Safe Content"
4. If both work correctly → Success! 🎉

## 🎯 What Vercel Does Automatically:
- ✅ Detects Python app from your code
- ✅ Installs Flask from requirements.txt
- ✅ Runs `python app.py` to start server
- ✅ Assigns you a free domain
- ✅ Handles HTTPS automatically

## 🔧 If You See Errors:
### Error: "No framework detected"
- Solution: Manually select "Python" from dropdown

### Error: "Build failed"
- Solution: Check requirements.txt has only `flask==3.0.3`

### Error: "Port already in use"
- Solution: Vercel handles this automatically - just wait

## 🎉 Expected Result:
- ✅ Live URL: `https://cyberbullying-detector.vercel.app`
- ✅ Working cyberbullying detection
- ✅ Free hosting forever
- ✅ No more deployment issues!

## 📞 Need Help?
If you get stuck at any step, tell me:
1. What step you're on
2. What error message you see
3. What Vercel shows on screen

I'll help you fix it immediately! 🚀
