# GitHub Token Setup Guide

## Problem: 401 Unauthorized Errors

If you're seeing `401 Unauthorized` errors when the agent tries to post comments or add reactions to GitHub, your `GITHUB_TOKEN` is either:
1. Missing or invalid
2. Expired or revoked
3. Missing required scopes/permissions

## Solution: Create/Update GitHub Token

### For Classic Personal Access Tokens

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Claude Code Agent")
4. Select expiration (or "No expiration" for long-lived tokens)
5. **Required Scopes:**
   - ✅ `repo` - Full control of private repositories (includes comments and reactions)
   - ✅ `public_repo` - If you only need access to public repositories

6. Click "Generate token"
7. **Copy the token immediately** (you won't see it again!)
8. Add to your `.env` file:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   ```

### For Fine-Grained Personal Access Tokens

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Configure:
   - **Token name**: "Claude Code Agent"
   - **Expiration**: Choose your preference
   - **Repository access**: Select specific repositories or "All repositories"
   
4. **Required Permissions:**
   - **Metadata**: `Read` (required for reactions)
   - **Repository contents**: `Read and write` (required for comments)
   - **Issues**: `Read and write` (required for issue comments)
   - **Pull requests**: `Read and write` (required for PR comments)

5. Click "Generate token"
6. Copy the token and add to `.env`:
   ```bash
   GITHUB_TOKEN=github_pat_your_token_here
   ```

## Verify Token Works

After setting the token, restart your application and try triggering a webhook. You should see:
- ✅ Immediate reaction (👀) on your comment
- ✅ Completion comment posted when task finishes
- ✅ No more `401 Unauthorized` errors in logs

## Troubleshooting

### Token Present but Still Getting 401?

1. **Check token format**: Classic tokens start with `ghp_`, fine-grained tokens start with `github_pat_`
2. **Verify scopes**: Classic tokens need `repo` scope, fine-grained tokens need `Metadata: read` and `Repository contents: write`
3. **Check expiration**: Token might have expired
4. **Verify repository access**: Fine-grained tokens must have access to the specific repository

### Check Token in Environment

```bash
# Check if token is set
python3 -c "import os; token = os.getenv('GITHUB_TOKEN'); print(f'Token present: {bool(token)}, Length: {len(token) if token else 0}')"
```

### Test Token Manually

```bash
# Test token with curl
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user
```

If this returns your user info, the token is valid. If you get 401, the token is invalid or expired.

## Security Best Practices

- ✅ Use fine-grained tokens when possible (more secure, least privilege)
- ✅ Set expiration dates
- ✅ Rotate tokens periodically
- ✅ Never commit tokens to git (use `.env` file, add to `.gitignore`)
- ✅ Use different tokens for different environments (dev/staging/prod)
