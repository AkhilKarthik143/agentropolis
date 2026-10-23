#!/usr/bin/env python3
"""Run a deterministic Agentropolis shock without starting the web server."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.api.economy import EconomyRuntime  # noqa: E402

runtime = EconomyRuntime()
shock = sys.argv[1] if len(sys.argv) > 1 else "supplier_bankruptcy"
result = runtime.engine.shock(shock)
print(json.dumps({"result": result, "events": len(runtime.engine.bus.replay()), "trial_balance": runtime.engine.ledger.trial_balance()}, indent=2, sort_keys=True))

