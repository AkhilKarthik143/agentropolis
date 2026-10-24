# Deployment and containers

`infra/docker/` contains the backend/frontend Dockerfiles and nginx configuration;
`docker-compose.yml` describes the local container topology. These files package
the independent Agentropolis services; they do not reference AgentPlace.

Docker configuration is supplied but was not executed in the current readiness
pass. Before public deployment, add authenticated ingress, managed secret storage,
tenant authorization, persistent database backups, provider reconciliation workers,
observability, and a reviewed migration strategy.
