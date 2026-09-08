# Mobile Clinical Companion Implementation Plan

## Gate1 control traceability

- Allow only verified HTTPS app links from approved domains.
- Require an authenticated and authorized session before opening clinical content.
- Validate every deep-link route and object identifier against an allowlist.
- Encrypt offline clinical data with a device-bound platform key.
- Apply a documented retention limit and securely purge data on logout.
- Prevent sensitive clinical content from appearing in backups or screenshots.
- Use the platform biometric API and require strong biometric authentication.
- Never store or process raw biometric templates in the application.
- Require server reauthentication for high-risk actions and after session expiry.

## Acceptance tests

- Verify link association, route allowlisting, tampered identifiers, and cross-tenant denial.
- Verify encrypted storage, backup exclusion, screenshot protection, expiry, and logout purge.
- Verify enrollment changes invalidate keys and high-risk APIs reject stale step-up tokens.
