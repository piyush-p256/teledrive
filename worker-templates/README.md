# TeleStore Worker Templates

These templates allow you to deploy your own file upload worker to handle uploads directly to Telegram.

## 🎉 Automatic Credential Management

**NEW**: Workers now automatically fetch credentials from your TeleStore backend! No need to manually configure bot tokens, channel IDs, or session strings in worker environment variables.

### How It Works
1. **User logs into Telegram** in TeleStore (QR code or phone)
2. **Creates bot via @BotFather** and adds token in TeleStore settings
3. **Worker fetches credentials** automatically using user's auth token
4. **Credentials are cached** at the worker for 1 hour (reduces backend calls)
5. **Auto-refresh** when cache expires or on worker restart

### Benefits
- ✅ No manual credential configuration in workers
- ✅ Credentials stay secure in your backend database
- ✅ Automatic updates when you change bot/channel
- ✅ Efficient caching reduces API calls
- ✅ Works across multiple workers seamlessly

---

## Quick Setup Instructions

### 1. Get Telegram API Credentials (One-time, Backend Only)
1. Visit https://my.telegram.org
2. Log in with your phone number
3. Go to "API development tools"
4. Create an app and save your `api_id` and `api_hash`
5. Add these to TeleStore backend `.env` file

### 2. Login to Telegram in TeleStore
1. Go to TeleStore Settings
2. Click "Connect Telegram"
3. Scan QR code or enter phone number
4. Your private channel will be created automatically

### 3. Create and Add Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow instructions
3. Copy your bot token
4. In TeleStore Settings, add the bot token
5. Bot will be automatically added as admin to your channel

### 4. Deploy Worker (see platform-specific instructions below)
- Only need to set `BACKEND_URL` environment variable
- No need to set bot tokens or channel IDs!

---

## Cloudflare Worker Deployment

### Prerequisites
- Cloudflare account
- Wrangler CLI installed (`npm install -g wrangler`)

### Steps
1. Create a new Cloudflare Worker
```bash
wrangler init telestore-worker
```

2. Copy `cloudflare-worker.js` content to `src/index.js`

3. Update BACKEND_URL in the code:
```javascript
const CONFIG = {
  BACKEND_URL: 'https://your-telestore-backend.com', // Your TeleStore backend
  MAX_FILE_SIZE: 2000 * 1024 * 1024,
  CACHE_DURATION: 3600000, // 1 hour
};
```

4. Deploy:
```bash
wrangler deploy
```

5. Copy the worker URL and use it in your TeleStore app for file uploads

**Note**: Credentials are fetched automatically from backend. No environment variables needed!

---

## Vercel Serverless Deployment

### Prerequisites
- Vercel account
- Vercel CLI installed (`npm install -g vercel`)

### Steps
1. Create a new project folder:
```bash
mkdir telestore-worker && cd telestore-worker
npm init -y
npm install form-data node-fetch
```

2. Create `api/upload.js` and copy `vercel-serverless.js` content

3. Create `vercel.json`:
```json
{
  "version": 2,
  "builds": [
    { "src": "api/**/*.js", "use": "@vercel/node" }
  ]
}
```

4. Set environment variable in Vercel dashboard:
   - `BACKEND_URL` - Your TeleStore backend URL

5. Deploy:
```bash
vercel
```

6. Copy the deployment URL + `/api/upload` and use it in your TeleStore app

**Note**: Only `BACKEND_URL` is required. Bot token and channel ID are fetched automatically!

---

## Render Deployment

### Prerequisites
- Render account

### Steps
1. Create a new project folder:
```bash
mkdir telestore-worker && cd telestore-worker
```

2. Copy `render-service.py` to the folder

3. Create `requirements.txt`:
```
Flask==3.0.0
requests==2.31.0
gunicorn==21.2.0
```

4. Create `render.yaml`:
```yaml
services:
  - type: web
    name: telestore-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn render-service:app
    envVars:
      - key: BACKEND_URL
        sync: false
```

5. Push to GitHub and connect to Render

6. Set `BACKEND_URL` environment variable in Render dashboard

7. Deploy and copy the service URL + `/upload`

**Note**: Only `BACKEND_URL` is required. Bot token and channel ID are fetched automatically!

---

## Testing Your Worker

Test with curl (you'll need your auth token from TeleStore):
```bash
curl -X POST https://your-worker-url/upload \
  -F "file=@test.jpg" \
  -F "userId=your-user-id" \
  -F "authToken=your-auth-token" \
  -F "fileName=test.jpg"
```

Expected response:
```json
{
  "success": true,
  "messageId": 123,
  "fileId": "xxx",
  "fileName": "test.jpg"
}
```

---

## How Credential Caching Works

### Cache Behavior
- **First Request**: Worker fetches credentials from backend using auth token
- **Subsequent Requests**: Uses cached credentials (1 hour validity)
- **Cache Expiry**: Automatically fetches fresh credentials after 1 hour
- **Worker Restart**: Cache is cleared, fetches on next request
- **Fallback**: If backend is unreachable, uses expired cache if available

### Performance Benefits
- Reduces backend API calls by 99%+ (typical 1000 uploads = 1 credential fetch)
- No latency overhead after first request
- Graceful degradation if backend is temporarily down

---

## Troubleshooting

### "Auth token required" error
- Make sure you're passing the user's auth token in upload requests
- Check that the token is valid (not expired)

### "Telegram not fully configured" error
- User needs to log into Telegram in TeleStore settings
- User needs to create and add a bot token in TeleStore settings

### "Failed to fetch credentials" error
- Check that `BACKEND_URL` is correct in worker config
- Verify backend is accessible from worker
- Check backend logs for authentication errors

### "Chat not found" error
- Make sure bot is added as admin to the channel
- This should happen automatically when bot token is added

### "File too large" error
- Telegram has a 2GB file size limit
- Worker might have timeout limits (adjust as needed)

### CORS errors
- Worker templates include CORS headers
- Check that your frontend URL is correct

---

## Security Notes

- ✅ Credentials never stored in worker code or environment variables
- ✅ Auth token required for credential access
- ✅ Credentials cached securely in worker memory only
- ✅ Automatic credential refresh ensures up-to-date access
- ✅ Each user's credentials isolated by auth token
- ⚠️ Use HTTPS for all worker deployments
- ⚠️ Never log or expose auth tokens

---

## Migration from Old Setup

If you previously configured workers with manual credentials:

1. **Remove old environment variables**: 
   - Delete `TELEGRAM_BOT_TOKEN`
   - Delete `TELEGRAM_CHANNEL_ID`
   - Delete `TELEGRAM_SESSION`
   - Keep only `BACKEND_URL`

2. **Update worker code**: 
   - Replace old worker code with new templates
   - Ensure `authToken` is passed in upload requests

3. **Update frontend upload logic**:
   - Include `authToken` in FormData when uploading

4. **Test thoroughly**: 
   - Verify uploads work
   - Check that credentials are being cached
   - Monitor backend logs for credential fetch requests

---

## Advanced Configuration

### Adjust Cache Duration

**Cloudflare Worker / Vercel:**
```javascript
const CONFIG = {
  CACHE_DURATION: 7200000, // 2 hours in milliseconds
};
```

**Render (Python):**
```python
CONFIG = {
    'CACHE_DURATION': 7200,  # 2 hours in seconds
}
```

### Disable Caching (Not Recommended)
Set `CACHE_DURATION` to `0` to fetch credentials on every request. This will increase backend load significantly.

---
