# Infrastructure coding-agent instructions

Keep backend, frontend, and database responsibilities explicit. Do not bake secrets
into images or copy `.env` files into build contexts. Use non-root containers where
practical, health checks, pinned/lockfile dependencies, and a writable persistent
data volume only where documented.

Run Docker build/compose checks only when Docker is available and use disposable
local data. Report exact image/build commands and distinguish configuration review
from an actually running deployment. Public deployment requires security review and
explicit user authorization.
