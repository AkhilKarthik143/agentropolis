# Security coding-agent instructions

Do not weaken scope, authorization, capability, or reset guards for convenience.
Validate all mutation inputs server-side; do not trust frontend role/business
claims. Keep secrets out of logs, events, screenshots, fixtures, and exceptions.

For security changes, run API guard, role guard, external-adapter safety, and
secret-scan checks. Document any new threat, environment variable, or deployment
limitation in `docs/security.md` and the relevant README.
