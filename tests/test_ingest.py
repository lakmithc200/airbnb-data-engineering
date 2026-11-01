import gzip
import json
from pathlib import Path
import pytest
from airbnb_lab.ingest import download, ingest, sha256, write_json, load_config
from airbnb_lab.pipeline import verified_outputs


def test_corrupted_cache_is_rejected_offline(tmp_path):
    cfg={'city':'demo','snapshot_date':'2026-01-01','country_path':'united-states/ny/albany','license':'CC BY 4.0','files':{'listings':'data/listings.csv.gz'}}
    with pytest.raises(ValueError,match='verified cached'):
        ingest(cfg,tmp_path,offline=True)


def test_verified_raw_reextracts_corrupted_derived_file(tmp_path):
    cfg={'city':'demo','snapshot_date':'2026-01-01','country_path':'united-states/ny/albany','license':'CC BY 4.0','files':{'listings':'data/listings.csv.gz'}}
    raw=tmp_path/'data/raw/demo/2026-01-01';raw.mkdir(parents=True)
    path=raw/'listings.csv.gz'
    with gzip.open(path,'wb') as f:f.write(b'id,price\n9007199254740993,$10\n')
    url='https://data.insideairbnb.com/united-states/ny/albany/2026-01-01/data/listings.csv.gz'
    write_json(raw/'manifest.json',{'files':{'listings':{'url':url,'sha256':sha256(path)}}})
    paths,_=ingest(cfg,tmp_path,offline=True)
    paths['listings'].write_text('damaged')
    paths,_=ingest(cfg,tmp_path,offline=True)
    assert '9007199254740993' in paths['listings'].read_text()


def test_output_hash_must_match(tmp_path):
    p=tmp_path/'artifact';p.write_text('good')
    manifest={'outputs':{'artifact':sha256(p)}}
    assert verified_outputs(manifest,tmp_path)
    p.write_text('broken')
    assert not verified_outputs(manifest,tmp_path)


def test_failed_download_cleans_partial_file(tmp_path,monkeypatch):
    def fail(*a,**k):raise OSError('network unavailable')
    monkeypatch.setattr('airbnb_lab.ingest.urlopen',fail)
    with pytest.raises(OSError):download('https://example.com',tmp_path/'x.csv',attempts=1)
    assert not (tmp_path/'x.csv').exists()
    assert not (tmp_path/'x.csv.part').exists()


def test_config_rejects_path_traversal(tmp_path):
    p=tmp_path/'config.json';p.write_text(json.dumps({'city':'../escape','snapshot_date':'2026-01-01'}))
    with pytest.raises(ValueError):load_config(p)
