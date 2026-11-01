# AI assistance disclosure

This personal project was developed with OpenAI Codex assistance. The exact underlying model version is not recorded; no specific model version is claimed.

AI-assisted work: source-brief interpretation, architecture, Python/SQL/tests, notebook, report generation, documentation, statistical design and review of outputs. The project owner should understand and validate these components before representing them professionally.

Key direction: build the provided Airbnb challenge as a personal experience and career-development project, with practical heads-ups. The original brief informed scope but was not republished.

Validation is based on executable evidence: downloaded source files, checksum manifests, synthetic edge-case tests, warehouse assertions, a real end-to-end run, SQL checks, notebook execution and visual artifact inspection. The final verification record states exactly which checks ran and which did not.

Substantive corrections made during implementation:

- Preserved large IDs as strings before any numeric inference.
- Distinguished the archive date from the observed scrape date.
- Handled source bathroom descriptions and account-duration fields when older columns were null.
- Skipped null GeoJSON geometry without dropping those listings from analytics.
- Left missing calendar price analyses unavailable.
- Kept fuzzy matches as review candidates.
- Used host-separated validation and reported the baseline win honestly.
- Added robust sensitivity tests after normality diagnostics showed strong skew.

No review text was sent to an external LLM. No API key, production deployment or autonomous pricing agent is included. The report's first-person learning advice is guidance for the owner, not a fabricated account of their experience.
