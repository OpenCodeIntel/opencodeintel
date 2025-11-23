# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

**Please DO NOT open public issues for security vulnerabilities.**

Instead:

1. **Email:** devanshu.sharma@northeastern.edu
2. **Subject:** `[SECURITY] CodeIntel Vulnerability Report`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## What to Expect

- **Acknowledgment:** Within 48 hours
- **Initial Assessment:** Within 1 week
- **Fix Timeline:** Depends on severity
  - Critical: 1-3 days
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Best effort

## Security Measures

CodeIntel implements:
- ✅ Rate limiting (tier-based quotas)
- ✅ API key authentication with SHA-256 hashing
- ✅ Input validation (SQL injection, path traversal prevention)
- ✅ Cost controls (max repo size, max repos per user)
- ✅ Request size limits (10MB max)
- ✅ Row-level security (user data isolation)

## Known Limitations

- API keys are stored hashed but transmitted in headers
- Use HTTPS in production (not HTTP)
- Dev mode (`DEBUG=true`) disables some security checks
- Row-level security requires Supabase configuration

## Best Practices

**For Deployment:**
- Always use HTTPS
- Set `DEBUG=false` in production
- Rotate API keys regularly
- Use environment variables for secrets
- Enable Supabase RLS policies

**For Development:**
- Never commit `.env` files
- Use strong API keys (not `dev-secret-key`)
- Keep dependencies updated
- Review security scanning results in CI/CD

## Credits

We appreciate responsible disclosure. Security researchers who report valid vulnerabilities will be credited (with permission) in our release notes.
