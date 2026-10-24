# Seed scenarios

`seed_economy.json` defines the reproducible ten-business local world used by the
demo and tests. `app/economy/scenarios.py` defines supported shocks such as supplier
bankruptcy, shortages, demand spikes, suspicious invoices, liquidity and payment
failures. `backend/scripts/run_scenario.py` is the scenario runner.

The default world starts paused so a presenter can inspect the initial coffee
contract, equipment approval, competing supplier offers, and agent state. A reset
creates a fresh local session/checkpoint; it does not contact an external bank or
provider.
