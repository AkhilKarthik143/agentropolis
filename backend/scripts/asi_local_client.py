#!/usr/bin/env python3
"""Offline ASI:One-shaped client for the Agentropolis gateway."""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.agents.gateway import GatewayService
from app.chat_utils import make_chat_message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="*", default=["Run the coffee purchase and recover if Northstar goes bankrupt."])
    args = parser.parse_args()
    message = make_chat_message(" ".join(args.request))
    result = GatewayService().handle_message(message)
    print(json.dumps(result.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
