# CRS Credit implementation-agent instructions

Mission: add only documented CRS sandbox risk/identity capabilities and keep them
advisory until the controller applies explicit policy.

Own `backend/app/integrations/crs_credit.py`, risk/credit policy code, fixtures and
tests. Do not create a live client until the official endpoint, schema, test
identities, retention rules, and credentials are provided.

Validate response schemas, missing data, supported attributes, provenance and
sensitive-data boundaries. Never fabricate a score or turn a mock score into a
provider claim. Run external-adapter, role-guard, scenario, and integrity tests.
Acceptance requires approved sandbox evidence that changes a simulated decision.
Update setup, matrix, track, security, and final-readiness docs; report human
blockers explicitly.
