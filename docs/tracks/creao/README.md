# Creao — AI-operated company workflow

## Goal and fit

Creao is a target track for a genuine workflow that helps a person create and
manage a company with AI employees. Agentropolis already has company creation,
business policies, role teams, approvals, procurement, finance reviews, and a
dashboard, but it has no verified Creao SDK/API or platform connection.

## Planned architecture

The local workflow uses `backend/app/api/economy.py`, `app/agents/company_agent.py`,
`app/agents/registry.py`, and the frontend business/agent views. A future Creao
adapter must be an explicit capability, not a label around existing Agentropolis
logic; it must map supported Creao actions to scoped tasks and preserve the trusted
engine boundary.

## Current and missing functionality

Local company/role configuration is available and tested. Creao status is
`NOT_STARTED` because platform meaning, API access, challenge rules, and
credential requirements are unverified.

## Test, demo, definition of done

Run API/agent/role tests and the frontend acceptance suite after handoff. The target
demo creates a company, assigns employees, sets objectives, delegates work, and
reviews/approves a real local workflow through Creao. Done requires genuine platform
use, provider evidence, and documented eligibility—not a mock adapter.
