# Security Policy

## Supported Versions

Security fixes are applied to the latest release line on main.

## Reporting a Vulnerability

Do not open public GitHub issues for vulnerabilities.

1. Email: security@akf.local (replace with your real security mailbox).
2. Include impact, reproduction steps, affected version, and suggested mitigation.
3. You will receive acknowledgment within 3 business days.

## Operational Security Baseline (Internal REST)

- Set AKF_ENV=prod in production.
- AKF_API_KEY is mandatory in prod mode.
- Restrict AKF_CORS_ORIGINS to known internal origins.
- Rotate API keys regularly and on personnel changes.
- Enable GitHub secret scanning and push protection at repository level.
- Keep Dependabot enabled and merge security updates promptly.
- Review logs for repeated 401/429 responses and anomalous request volume.
