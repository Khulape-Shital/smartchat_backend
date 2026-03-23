# Deployment Guide - Render

This guide walks through deploying the SmartChat backend to [Render](https://render.com).

## Prerequisites

- Render account (free tier available)
- GitHub repository with code pushed
- Environment variables configured

## Deployment Methods

### Method 1: Using render.yaml (Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add Dockerfile and render.yaml"
   git push origin main
   ```

2. **Create Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Select your GitHub repository
   - Render will auto-detect `render.yaml`
   - Click "Create Web Service"

3. **Configure Environment**
   - Render automatically creates PostgreSQL database from `render.yaml`
   - Set additional env vars as needed

### Method 2: Manual Deployment

1. **Create Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Select your GitHub repository
   - Choose a name: `smartchat-backend`

2. **Build Settings**
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** 
     ```
     gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
     ```

3. **Environment Variables**
   
   Add these in Render dashboard (Settings → Environment):
   ```
   DATABASE_URL=postgresql://...  (from PostgreSQL database)
   ENVIRONMENT=production
   JWT_SECRET=your_secret_key_here
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=587
   SMTP_USERNAME=your_email
   SMTP_PASSWORD=your_app_password
   PROJECT_NAME=SmartChat
   ```

4. **Create PostgreSQL Database**
   - Go to Render Dashboard
   - Click "New +" → "PostgreSQL"
   - Set name: `smartchat-db`
   - Copy connection string to `DATABASE_URL`

5. **Deploy**
   - Click "Deploy"
   - Monitor logs in Render dashboard
   - Once deployed, you'll get a public URL

## Database Setup

### Initial Migration
- Render runs migrations automatically via `render.yaml`
- Check logs: Settings → Logs

### Manual Migrations
Connect to database:
```bash
psql postgresql://user:password@host:port/dbname
```

Run migrations:
```bash
alembic upgrade head
```

## Troubleshooting

### Issue: Build fails with "ModuleNotFoundError"
- ✅ Ensure all imports are in `requirements.txt`
- ✅ Check Python version compatibility
- ✅ Clear cache: Settings → Restart

### Issue: Database connection refused
- ✅ Verify `DATABASE_URL` is set correctly
- ✅ Ensure PostgreSQL service is running
- ✅ Check firewall/security rules

### Issue: Port binding error
- ✅ Render uses `PORT` env var automatically
- ✅ Don't hardcode port, use: `--bind 0.0.0.0:$PORT`

### Issue: Migrations not running
- ✅ Check if alembic.ini path is correct: `sqlalchemy.url = driver://user:pass@localhost/dbname`
- ✅ Or set `SQLALCHEMY_DATABASE_URL` env var
- ✅ Run manually: Settings → Shell

### Issue: Large deployment time
- ✅ Free tier is slower; use paid plans for faster builds
- ✅ Pre-build Docker image locally for faster deployment

## Docker Testing Locally

Test Docker build locally before deploying:

```bash
docker build -t smartchat-backend .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://localhost/smartchat" \
  -e JWT_SECRET="test_secret" \
  smartchat-backend
```

Access: `http://localhost:8000`

## Frontend Configuration

Update frontend `.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=https://your-render-url.onrender.com/api
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id
```

## Monitoring

- **Logs:** Settings → Logs
- **Metrics:** Settings → Monitoring
- **Errors:** Check application logs for stack traces

## Scaling

### Upgrade from Free to Paid
- Go to Settings → Plan
- Select paid tier (Standard $7/mo)
- Benefits: Always-on service, better resources, custom domains

### Auto-scaling (Pro)
- Available on paid tiers
- Configure in Settings → Auto-scaling

## SSL/HTTPS

- Render provides free SSL certificates
- HTTPS enabled by default on `*.onrender.com` domains
- Custom domains: Go to Settings → Custom Domains

## Useful Commands

```bash
# View Render logs
curl https://your-app.onrender.com/docs

# Check health
curl https://your-app.onrender.com/health

# Database shell access
Render Dashboard → PostgreSQL → Connect → psql command
```

## Support

- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [GitHub Issues](link_to_your_repo)
