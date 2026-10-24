# Core configuration

`app/core/config.py` owns standalone process settings: loopback host/port, data
directory, SQLite store mode, seed, LLM mode, frontend origin and CORS origins.
Configuration is read from the Agentropolis root `.env`; `.env.example` is the
public template. No AgentPlace environment is loaded.

Use local defaults for development. Provider-specific configuration remains in the
provider adapter and its documented environment variables. Do not add secrets to
the settings dataclass or log values that may contain credentials.
