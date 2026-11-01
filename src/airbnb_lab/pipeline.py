"""Orchestration, lineage, failure metadata, and snapshot-level incremental work."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import time
import pandas as pd
from .ingest import ingest, sha256, write_json
from .quality import clean_inputs, profile
from .warehouse import build

LOG = logging.getLogger(__name__)


def code_digest():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def verified_outputs(manifest, root):
    return bool(manifest.get("outputs")) and all((root/rel).exists() and sha256(root/rel) == checksum for rel,checksum in manifest["outputs"].items())


def run(config, root, offline=False, force=False):
    started = time.monotonic()
    output = root / "outputs" / config["city"] / config["snapshot_date"]
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "run_manifest.json"
    warehouse = root / "data/warehouse" / config["city"] / f"{config['snapshot_date']}.duckdb"
    old = json.loads(log_path.read_text()) if log_path.exists() else {}
    metadata = {"started_at": datetime.now(timezone.utc).isoformat(), "status": "running", "city": config["city"], "snapshot_date": config["snapshot_date"]}
    try:
        paths, source = ingest(config, root, offline)
        versions = {x: importlib.metadata.version(x) for x in ["pandas", "numpy", "scipy", "scikit-learn", "duckdb", "statsmodels", "matplotlib", "reportlab"]}
        identity = {"sources": {k:v["sha256"] for k,v in source["files"].items()}, "config": config, "code": code_digest(), "versions": versions, "python": platform.python_version()}
        fingerprint = hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        if not force and old.get("fingerprint") == fingerprint and old.get("status") == "success" and verified_outputs(old, root):
            LOG.info("Unchanged snapshot and verified outputs; skipping processing: %s", output)
            return {"status": "skipped", "output": str(output)}
        metadata.update(fingerprint=fingerprint, environment=versions, python=platform.python_version())
        write_json(log_path, metadata)
        raw = {key: pd.read_csv(path,dtype="string") for key,path in paths.items() if path.suffix == ".csv"}
        profiles = {key: profile(frame) for key,frame in raw.items()}
        boundary = json.loads(paths["boundaries"].read_text(encoding="utf-8"))
        profiles["boundaries"] = {"features": len(boundary["features"]), "null_geometries": sum(f.get("geometry") is None for f in boundary["features"]), "geometry_types": sorted({f["geometry"]["type"] for f in boundary["features"] if f.get("geometry")}), "properties": sorted({key for f in boundary["features"] for key in f["properties"]})}
        tables, audit = clean_inputs(raw, config)
        # Do not expose public source identifiers in shareable quality artifacts.
        pairs = audit.pop("fuzzy_candidate_pairs")
        audit["fuzzy_candidate_pair_count"] = len(pairs)
        write_json(output / "private/fuzzy_candidates.json", pairs)
        write_json(output / "schema_profile.json", profiles)
        write_json(output / "quality_report.json", audit)
        write_json(output / "source_manifest.json", source)
        LOG.info("Building snapshot warehouse")
        metadata["row_counts"] = build(tables, warehouse, config)
        from .analysis import analyze
        LOG.info("Running statistics and host-separated model evaluation")
        results, residuals, _ = analyze(tables, config)
        write_json(output / "analysis.json", results)
        for key in ["neighbourhoods", "room_types", "host_segments", "calendar_months", "review_months", "descriptive", "correlations"]:
            pd.DataFrame(results[key]).to_csv(output / f"{key}.csv",index=False)
        from .charts import create as charts
        from .dashboard import create as dashboard
        figures = charts(tables, results, residuals, paths["boundaries"], output / "figures", config["currency"])
        dashboard(tables["listings"], config, results, output / "explorer.html")
        from .report import create as report
        report(config, results, audit, profiles, figures, output / "market_report.pdf")
        metadata.update(status="success", completed_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-started,2),
                        lineage={"dim_listing": "detailed listings + review counts + calendar coverage", "dim_host": "clean listings grouped by host_id", "dim_date": "distinct review/calendar dates", "dim_neighbourhood": "distinct clean listing neighbourhoods", "fact_calendar": "validated calendar listing/date rows", "fact_review": "deduplicated review id/listing/date; reviewer text removed", "reports": "clean warehouse-equivalent frames -> analysis -> figures, HTML, PDF"})
        artifacts = [p for p in output.rglob("*") if p.is_file() and p != log_path and "private" not in p.parts] + [warehouse]
        metadata["outputs"] = {p.relative_to(root).as_posix():sha256(p) for p in artifacts}
        write_json(log_path, metadata)
        LOG.info("Completed in %.1fs: %s", time.monotonic()-started, output)
        return metadata
    except Exception as exc:
        metadata.update(status="failed", error=f"{type(exc).__name__}: {exc}", elapsed_seconds=round(time.monotonic()-started,2))
        write_json(log_path, metadata)
        LOG.exception("Pipeline failed; raw inputs are retained")
        raise
