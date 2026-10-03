# Render Deployment Configuration Guide

## Step-by-Step Render Setup

### 1. Create Web Service

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if not already connected
4. Find repository: **reet-lab/medical-document-verifier**
5. Click **"Connect"**

---

## 2. Basic Settings

### General
- **Name:** `medical-document-verifier`
- **Region:** Choose closest to your users (e.g., Oregon (US West), Ohio (US East), Frankfurt (EU))
- **Branch:** `main`
- **Root Directory:** (leave blank)
- **Runtime:** `Python 3`

### Build & Deploy
- **Build Command:**
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```

- **Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### Instance Type
- **Plan:** `Free` (or select paid plan for production)
  - Free tier: 512 MB RAM, shared CPU
  - Spins down after 15 minutes of inactivity
  - 750 hours/month free

---

## 3. Environment Variables

Add these in the **"Environment"** section:

### Required Variables

| Key | Value | Description |
|-----|-------|-------------|
| `PYTHON_VERSION` | `3.12.1` | Python version (Render auto-detects from render.yaml) |
| `PORT` | (auto-set by Render) | Don't set this - Render provides it automatically |

### Recommended Variables

| Key | Value | Description |
|-----|-------|-------------|
| `DEBUG` | `false` | Disable debug mode in production |
| `RELOAD` | `false` | Disable auto-reload in production |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `MAX_FILE_SIZE_MB` | `10` | Maximum upload size in MB |
| `MAX_IMAGE_WIDTH` | `4096` | Maximum image width in pixels |
| `MAX_IMAGE_HEIGHT` | `4096` | Maximum image height in pixels |
| `CONFIDENCE_THRESHOLD` | `0.7` | Classification confidence threshold |

### CORS Configuration

| Key | Value | Description |
|-----|-------|-------------|
| `CORS_ORIGINS` | `*` | For testing: allow all origins |

**For production, use specific origins:**
```
https://yourapp.com,https://www.yourapp.com,https://app.yourapp.com
```

### Optional Variables

| Key | Value | Description |
|-----|-------|-------------|
| `API_TITLE` | `Medical Document Verification API` | API title (has default) |
| `API_VERSION` | `1.0.0` | API version (has default) |
| `MODEL_PATH` | (leave blank) | Path to trained model if you have one |

---

## 4. Advanced Settings

### Health Check Path
- **Health Check Path:** `/health`
- **Health Check Interval:** 30 seconds (default)

Render will automatically check this endpoint to verify your service is running.

### Auto-Deploy
- ✅ **Enable:** Auto-deploy from `main` branch
  
Every push to `main` will trigger a new deployment automatically.

---

## 5. Complete Configuration Example

Here's what your Render service settings should look like:

```yaml
Name: medical-document-verifier
Region: Oregon (US West)
Branch: main
Runtime: Python 3

Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT

Environment Variables:
  PYTHON_VERSION=3.12.1
  DEBUG=false
  RELOAD=false
  LOG_LEVEL=INFO
  MAX_FILE_SIZE_MB=10
  MAX_IMAGE_WIDTH=4096
  MAX_IMAGE_HEIGHT=4096
  CONFIDENCE_THRESHOLD=0.7
  CORS_ORIGINS=*

Health Check: /health
Auto-Deploy: Enabled
```

---

## 6. After Creating Service

### Monitor First Deploy
1. Watch the **Logs** tab in real-time
2. Look for successful messages:
   ```
   Building...
   Installing dependencies...
   Starting service...
   Application startup complete
   Uvicorn running on http://0.0.0.0:XXXXX
   ```

3. Wait 2-5 minutes for first deployment

### Test Your API

Once deployed, you'll get a URL like:
```
https://medical-document-verifier.onrender.com
```

Test endpoints:

```bash
# Health check
curl https://medical-document-verifier.onrender.com/health

# Service status
curl https://medical-document-verifier.onrender.com/api/v1/status

# API documentation
open https://medical-document-verifier.onrender.com/docs
```

---

## 7. Common Issues & Solutions

### Build Fails: "Python version not found"
**Solution:** Remove or update `PYTHON_VERSION` to `3.12.1`

### Build Fails: "Cannot install package X"
**Solution:** Check requirements.txt has version ranges, not exact pins

### Service Won't Start: "Address already in use"
**Solution:** Ensure start command uses `$PORT` variable, not hardcoded port

### 503 Service Unavailable (Free Tier)
**Solution:** Service is spinning up from inactivity - wait 30-60 seconds

### CORS Errors from Frontend
**Solution:** Add your frontend domain to `CORS_ORIGINS`:
```
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
```

### Health Check Failing
**Solution:** Verify `/health` endpoint is accessible and returns 200 status

---

## 8. Production Checklist

Before going to production:

- [ ] Set specific `CORS_ORIGINS` (not `*`)
- [ ] Set `DEBUG=false`
- [ ] Set `LOG_LEVEL=INFO` or `WARNING`
- [ ] Configure custom domain (if needed)
- [ ] Set up monitoring and alerts
- [ ] Enable HTTPS (automatic on Render)
- [ ] Consider upgrading from Free tier
- [ ] Set up database if needed (add as separate service)
- [ ] Configure rate limiting (add middleware or use Render features)
- [ ] Review upload limits for your use case

---

## 9. Monitoring & Logs

### View Logs
- Go to your service in Render dashboard
- Click **"Logs"** tab
- See real-time application logs

### Metrics
- **Events:** Deployment history
- **Metrics:** CPU, Memory, Request stats (paid plans)

### Set Up Alerts
- Configure email/Slack notifications for:
  - Deploy failures
  - Service down
  - High error rates

---

## 10. Scaling & Upgrades

### Free Tier Limitations
- ❌ Spins down after 15 minutes inactivity
- ❌ 512 MB RAM
- ❌ Shared CPU
- ✅ 750 hours/month free

### Upgrade to Starter ($7/month)
- ✅ Always-on (no spin down)
- ✅ 512 MB RAM
- ✅ Dedicated resources
- ✅ Better performance

### When to Upgrade
- You need zero-downtime
- You have consistent traffic
- First request time is critical
- You're getting production users

---

## Quick Start Commands

After deployment, save these for testing:

```bash
# Set your URL
export API_URL="https://medical-document-verifier.onrender.com"

# Health check
curl $API_URL/health

# API status
curl $API_URL/api/v1/status

# Upload test document (replace with actual image)
curl -X POST $API_URL/api/v1/verify-document \
  -F "file=@test-document.jpg"

# Open interactive docs
open $API_URL/docs
```

---

## Support & Resources

- **Render Docs:** https://render.com/docs
- **Render Status:** https://status.render.com
- **Community:** https://community.render.com
- **FastAPI Docs:** https://fastapi.tiangolo.com

---

## Your Deployment URL

After deployment, your API will be live at:

🔗 **https://medical-document-verifier.onrender.com**

**Endpoints:**
- Health: `/health`
- Status: `/api/v1/status`
- Verify: `/api/v1/verify-document` (POST)
- Docs: `/docs`
- OpenAPI: `/openapi.json`

---

**Ready to deploy!** Follow the settings above in your Render dashboard.
