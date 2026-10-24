# Script-agent instructions

Keep scripts safe, deterministic, and explicit about scope. Use `set -euo
pipefail` for shell scripts, quote paths/variables, avoid destructive broad globs,
and fail closed for missing credentials. Do not embed secrets or assume a port is
free when a caller can configure it.

Run `bash -n scripts/*.sh backend/scripts/*.sh`, the relevant script, and the
documentation check after changes. Report whether a script starts/stops processes,
mutates demo data, contacts a provider, or only performs read-only validation.
