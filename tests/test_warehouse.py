import duckdb
from airbnb_lab.quality import clean_inputs
from airbnb_lab.warehouse import build
from test_quality import inputs


def test_star_grain_and_no_join_fanout(tmp_path):
    tables,_=clean_inputs(inputs(),{'snapshot_date':'2026-09-14'})
    db=tmp_path/'snapshot.duckdb'
    counts=build(tables,db,{'city':'demo','snapshot_date':'2026-09-14','currency':'USD'})
    assert counts['dim_listing']==2
    with duckdb.connect(str(db),read_only=True) as c:
        assert c.execute('SELECT count(*) FROM fact_calendar JOIN dim_listing ON listing_id=id').fetchone()[0]==3
        assert c.execute("SELECT id FROM dim_listing WHERE id='9007199254740993'").fetchone()[0]=='9007199254740993'
        assert c.execute('SELECT sum(known_days) FROM mart_calendar_month').fetchone()[0]==2
    # A rebuild replaces the snapshot, never appends duplicate facts.
    assert build(tables,db,{'city':'demo','snapshot_date':'2026-09-14','currency':'USD'})==counts
