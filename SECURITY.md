# Security Policy

## Reporting Security Issues

If you discover a security vulnerability, please email [your-email] instead of using the issue tracker.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

**DO NOT include:**
- Your actual API keys
- Real credentials or tokens
- Production URLs or endpoints

## Supported Versions

Currently supporting: [version]

## Security Best Practices

- Never commit .env files
- Rotate API keys if accidentally exposed
- Use environment variables for all secrets
- Keep dependencies updated

## Security Checklist Before Committing

- [ ] `.env` is in `.gitignore` and NOT staged
- [ ] No API keys in code or comments
- [ ] `.env.example` has only placeholder values
- [ ] Error messages don't expose secrets
- [ ] Logs are sanitized
