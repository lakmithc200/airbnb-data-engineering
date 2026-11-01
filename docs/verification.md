# Verification record

Validated on 1 November 2026 with Python 3.12 on Windows.

- Real-data pipeline completed successfully: seven downloaded files, 500 listings, 200 hosts, 182,500 calendar rows and 30,251 reviews.
- 14 automated tests passed, covering currency parsing, large IDs, nullable availability, schema changes, duplicate/orphan removal, source-cache integrity, failed download cleanup, warehouse grain and model evaluation contracts.
- Editable package installation succeeded; `pip check` reported no broken requirements.
- All notebook cells executed successfully against the generated warehouse.
- The 22-page PDF was rendered and visually inspected across every page; no clipping or overflow was observed.
- Source and output checksum manifests accompany the run. The warehouse is local and excluded from Git.
- An unchanged offline rerun correctly skipped processing after checking output hashes. All six SQL examples executed successfully.

Limitations of verification: the in-app browser's URL policy blocked the local HTML file, so browser rendering and interaction have not been visually verified. Docker's daemon was unavailable, so the supplied Compose configuration was not executed. GitHub Actions has not yet been observed running. No cloud deployment was attempted.

The explorer can be opened directly in a local browser after downloading or cloning the repository. The README links to the actual report and source artifacts. Statistical/model results are descriptive experiments, not production guarantees.
