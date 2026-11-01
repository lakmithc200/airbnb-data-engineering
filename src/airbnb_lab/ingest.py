"""Pinned snapshot ingestion with checksums, retry, and atomic file promotion."""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import re
import shutil
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

LOG = logging.getLogger(__name__)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, default=str, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9-]+", config["city"]):
        raise ValueError("city must be a lowercase slug")
    date.fromisoformat(config["snapshot_date"])
    if not re.fullmatch(r"[A-Z]{3}", config["currency"]):
        raise ValueError("currency must be a three-letter ISO code")
    if not re.fullmatch(r"[a-z0-9/-]+", config["country_path"]) or ".." in config["country_path"]:
        raise ValueError("Invalid source path")
    for key, value in config["files"].items():
        if not re.fullmatch(r"[a-z_]+", key) or not re.fullmatch(r"(?:data|visualisations)/[a-z.]+", value):
            raise ValueError("Invalid file configuration")
    return config


def download(url: str, path: Path, attempts: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "AirbnbMarketLab/1.0 (personal research)"})
            with urlopen(request, timeout=90) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out)
                expected = response.headers.get("Content-Length")
            if expected and partial.stat().st_size != int(expected):
                raise ValueError("Incomplete download")
            if partial.stat().st_size == 0:
                raise ValueError("Empty download")
            if path.suffix == ".gz":
                # Validate the entire gzip stream/CRC, not just its header.
                with gzip.open(partial, "rb") as stream:
                    while stream.read(1024 * 1024):
                        pass
            partial.replace(path)
            return
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt + 1 == attempts:
                raise
            LOG.warning("Download retry %s for %s", attempt + 1, url)
            time.sleep(2 ** attempt)


def ingest(config: dict, root: Path, offline: bool = False) -> tuple[dict, dict]:
    raw = root / "data/raw" / config["city"] / config["snapshot_date"]
    extracted = root / "data/extracted" / config["city"] / config["snapshot_date"]
    extracted.mkdir(parents=True, exist_ok=True)
    manifest_path = raw / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    paths, files = {}, {}
    base = f"https://data.insideairbnb.com/{config['country_path']}/{config['snapshot_date']}"
    for key, relative in config["files"].items():
        suffix = ".csv.gz" if relative.endswith(".gz") else Path(relative).suffix
        target = raw / (key + suffix)
        url = f"{base}/{relative}"
        prior = previous.get("files", {}).get(key, {})
        valid = target.exists() and prior.get("sha256") == sha256(target) and prior.get("url") == url
        if not valid:
            if offline:
                raise ValueError(f"No verified cached input for {key}; run ingest online first")
            LOG.info("Downloading %s", url)
            download(url, target)
        digest = sha256(target)
        output = extracted / (key + (".csv" if suffix.endswith("gz") else suffix))
        # Re-extract on every invocation so corrupted derived caches cannot survive.
        partial = output.with_suffix(output.suffix + ".tmp")
        opener = gzip.open if suffix.endswith("gz") else open
        with opener(target, "rb") as src, partial.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        partial.replace(output)
        paths[key] = output
        files[key] = {"url": url, "sha256": digest, "bytes": target.stat().st_size,
                      "downloaded_at": prior.get("downloaded_at") if valid else datetime.now(timezone.utc).isoformat()}
    manifest = {"city": config["city"], "snapshot_date": config["snapshot_date"],
                "license": config["license"], "files": files}
    write_json(manifest_path, manifest)
    return paths, manifest
