# 🚀 Quick ngrok Setup (Fix for "1 simultaneous session" error)

## The Problem
ngrok free tier only allows 1 tunnel at a time. The error you're seeing means you already have an ngrok session running somewhere.

## ✅ Solution 1: Use ngrok Config (Recommended)

The `ngrok.yml` file allows you to run **all webhook endpoints through a single tunnel**.

### Steps:

1. **Set your ngrok auth token** (one-time setup):
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```
   Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken

2. **Start the tunnel**:
   ```bash
   make tunnel
   ```

3. **Copy the public URL** (e.g., `https://abc123.ngrok.io`)

4. **Update your .env**:
   ```bash
   WEBHOOK_PUBLIC_DOMAIN=https://abc123.ngrok.io
   ```

5. **Restart the app**:
   ```bash
   make rebuild
   ```

Now all these endpoints work through ONE tunnel:
- `https://abc123.ngrok.io/webhooks/github`
- `https://abc123.ngrok.io/webhooks/jira`
- `https://abc123.ngrok.io/webhooks/slack`
- `https://abc123.ngrok.io/webhooks/gitlab`
- `https://abc123.ngrok.io/webhooks/custom/{id}`

## ✅ Solution 2: Use Cloudflare Tunnel (Free, No Limits!)

Better option - no session limits at all!

1. **Install cloudflared**:
   ```bash
   brew install cloudflared
   ```

2. **Start tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Copy the URL** and update `.env`

## 🔍 Troubleshooting

### "ERR_NGROK_108: authentication failed"

**Check for existing sessions:**
```bash
# Kill all ngrok processes
pkill ngrok

# Or check what's running
ps aux | grep ngrok
```

**View your active sessions:**
https://dashboard.ngrok.com/agents

**Then restart:**
```bash
make tunnel
```

### Still getting errors?

1. Make sure you've added your auth token:
   ```bash
   ngrok config add-authtoken YOUR_TOKEN
   ```

2. Check if ngrok.yml exists:
   ```bash
   ls -la ngrok.yml
   ```

3. Try cloudflared instead (no limits):
   ```bash
   brew install cloudflared
   cloudflared tunnel --url http://localhost:8000
   ```

## 📖 Next Steps

Once your tunnel is running:

1. ✅ Copy the public URL
2. ✅ Update `WEBHOOK_PUBLIC_DOMAIN` in `.env`
3. ✅ Restart: `make rebuild`
4. ✅ Create webhooks in dashboard
5. ✅ Configure service webhooks (GitHub, Jira, etc.)

See `docs/WEBHOOK-SETUP.md` for detailed webhook configuration.
