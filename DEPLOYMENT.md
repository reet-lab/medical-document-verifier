# Deployment Guide

## GitHub Setup

### Your repository is ready to push!

Run these commands after creating your GitHub repository:

```bash
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/medical-document-verifier.git
git push -u origin main
```

Or with SSH:
```bash
git remote add origin git@github.com:YOUR_USERNAME/medical-document-verifier.git
git push -u origin main
```

## Deploy to Render

### Prerequisites
- GitHub account with your repository pushed
- Render account (sign up at https://render.com)

### Deployment Steps

1. **Sign in to Render**
   - Go to https://dashboard.render.com
   - Sign in with GitHub (recommended) or email

2. **Connect Your Repository**
   - Click **"New +"** → **"Web Service"**
   - Connect your GitHub account if not already connected
   - Find and select your `medical-document-verifier` repository

3. **Configure the Service**
   
   Render will auto-detect your `render.yaml` file. Verify these settings:
   
   - **Name:** `medical-document-verifier`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (or select your preferred plan)

4. **Environment Variables**
   
   Add these in the Render dashboard under "Environment":
   
   ```
   PYTHON_VERSION=3.13
   DEBUG=false
   RELOAD=false
   LOG_LEVEL=INFO
   CORS_ORIGINS=https://your-frontend-domain.com
   ```
   
   Optional (use defaults if not set):
   ```
   MAX_FILE_SIZE_MB=10
   MAX_IMAGE_WIDTH=4096
   MAX_IMAGE_HEIGHT=4096
   CONFIDENCE_THRESHOLD=0.7
   ```

5. **Deploy**
   - Click **"Create Web Service"**
   - Render will build and deploy automatically
   - Wait 2-5 minutes for the first deployment

6. **Verify Deployment**
   
   Once deployed, you'll get a URL like: `https://medical-document-verifier.onrender.com`
   
   Test endpoints:
   ```bash
   # Health check
   curl https://medical-document-verifier.onrender.com/health
   
   # API status
   curl https://medical-document-verifier.onrender.com/api/v1/status
   
   # Upload test (replace with actual image path)
   curl -X POST https://medical-document-verifier.onrender.com/api/v1/verify-document \
     -F "file=@test-image.jpg"
   ```

7. **Access API Documentation**
   - Interactive docs: `https://your-app.onrender.com/docs`
   - ReDoc: `https://your-app.onrender.com/redoc`
   - OpenAPI spec: `https://your-app.onrender.com/openapi.json`

## Important Notes

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds (cold start)
- 750 hours/month of free runtime
- Consider upgrading for production use

### Security for Production
Before going live with real data:

1. **CORS Configuration**
   - Set specific origins in `CORS_ORIGINS`, don't use `*`
   - Example: `CORS_ORIGINS=https://app.example.com,https://www.example.com`

2. **Rate Limiting**
   - Add rate limiting middleware or use Render's built-in protection
   - Consider adding authentication/authorization

3. **HTTPS**
   - Render provides free SSL certificates automatically
   - Always use HTTPS URLs in production

4. **Monitoring**
   - Enable Render's logging and metrics
   - Set up health check alerts
   - Monitor error rates and response times

5. **Secrets Management**
   - Never commit `.env` files
   - Use Render's environment variables for secrets
   - Rotate API keys regularly

### Auto-Deploy
Render automatically deploys when you push to the `main` branch. To deploy changes:

```bash
git add .
git commit -m "Your commit message"
git push origin main
```

### Manual Deploy
You can also trigger manual deploys from the Render dashboard.

## Troubleshooting

### Build Fails
- Check Python version compatibility (3.13)
- Verify `requirements.txt` has all dependencies
- Check Render build logs for specific errors

### Service Won't Start
- Verify start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Check logs in Render dashboard
- Ensure `PORT` environment variable is used (Render sets this automatically)

### 503 Service Unavailable
- Check if service is spinning up (free tier)
- Verify health check endpoint returns 200
- Check application logs for startup errors

### CORS Errors
- Add your frontend domain to `CORS_ORIGINS`
- Verify the format: comma-separated, no spaces
- Restart the service after changing environment variables

### Image Upload Fails
- Check file size limits (default 10MB)
- Verify image format (JPEG/PNG only)
- Check application logs for validation errors

## Monitoring Your Deployment

### Render Dashboard
- View logs in real-time
- Check metrics (CPU, memory, response times)
- Monitor deploy history
- Set up health check alerts

### API Health Endpoints
```bash
# Basic health
curl https://your-app.onrender.com/health

# Service status with classifier info
curl https://your-app.onrender.com/api/v1/status
```

## Next Steps

1. **Test thoroughly** with real document images
2. **Configure CORS** for your frontend application
3. **Set up monitoring** and alerting
4. **Add authentication** if required for your use case
5. **Train and deploy** a real classifier when you have labeled data
6. **Document your API** usage for consumers
7. **Set up CI/CD** for automated testing before deploy

## Support

- Render Documentation: https://render.com/docs
- Render Community: https://community.render.com
- FastAPI Documentation: https://fastapi.tiangolo.com

## Cost Estimates

### Free Tier
- **Cost:** $0/month
- **Includes:** 750 hours, 512MB RAM, automatic SSL
- **Best for:** Development, testing, low-traffic apps

### Starter Plan (~$7/month)
- **Cost:** Starting at $7/month
- **Includes:** Always-on service, 512MB RAM, no cold starts
- **Best for:** Production apps with moderate traffic

### Professional Plans
- Higher memory and CPU options
- Better performance and scaling
- Contact Render for pricing

---

**Ready to deploy!** Follow the steps above to get your Medical Document Verification API live on Render.
