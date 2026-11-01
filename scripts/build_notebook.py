"""Regenerate the learning notebook; execute separately with nbclient/Jupyter."""
from pathlib import Path
import nbformat as nb

root=Path(__file__).resolve().parents[1]
notebook=nb.v4.new_notebook()
cells=[]
def md(text):cells.append(nb.v4.new_markdown_cell(text))
def code(text):cells.append(nb.v4.new_code_cell(text))
md("""# Airbnb Market Lab: a guided walkthrough

An AI-assisted personal project using real Inside Airbnb Albany data. Run the CLI once before this notebook. All results below come from saved analytical outputs or SQL; there is no network call or secret key in this notebook.

**First question:** what does the data actually measure? Listed prices and available calendar states are not realised bookings or revenue. The snapshot archive is dated 2026-09-14, while the listing scrape date is 2026-09-16.
""")
code("""from pathlib import Path
import json
import duckdb
import pandas as pd
from IPython.display import display, Image

ROOT = Path.cwd()
if not (ROOT / 'configs').exists():
    ROOT = ROOT.parent
OUT = ROOT / 'outputs/albany/2026-09-14'
DB = ROOT / 'data/warehouse/albany/2026-09-14.duckdb'
assert DB.exists(), 'Run python -m airbnb_lab.cli run first.'
results = json.loads((OUT / 'analysis.json').read_text())
quality = json.loads((OUT / 'quality_report.json').read_text())
con = duckdb.connect(str(DB), read_only=True)
pd.Series(results['summary'], name='value').to_frame()
""")
md("""## 1. Check the grain before joining

One database is one city/snapshot. Calendar facts are unique on listing ID plus calendar date; review facts have unique review IDs. Large IDs remain strings. A join that changes the fact count indicates a grain error.
""")
code("""display(con.execute('SHOW TABLES').df())
con.execute('''SELECT
  (SELECT count(*) FROM fact_calendar) AS before_join,
  (SELECT count(*) FROM fact_calendar c JOIN dim_listing l ON c.listing_id=l.id) AS after_join
''').df()
""")
md("""## 2. Read the quality report

Missing prices stay missing. Similar-title records are candidates for manual review, not deletions. Numeric bathrooms are recovered from explicit descriptions; account tenure is approximate where only duration components are available.
""")
code("""pd.Series(quality, dtype=object).to_frame('observed')""")
md("""## 3. Compare prices within segments

Only positive-price listings enter these comparisons. Count the priced records and compare room types before attributing differences to neighbourhood. Means can be pulled upward by extreme values.
""")
code("""con.execute('''
SELECT room_type, count(*) AS listings,
       count(*) FILTER (WHERE price > 0) AS priced,
       median(price) FILTER (WHERE price > 0) AS median_price,
       avg(price) FILTER (WHERE price > 0) AS mean_price
FROM dim_listing GROUP BY room_type ORDER BY listings DESC
''').df()
""")
code("display(Image(filename=str(OUT / 'figures/price_distribution.png'), width=850))")
md("""## 4. Availability is not occupancy

The denominator below is known calendar states. No prices are present in this calendar snapshot. Do not copy listing prices onto calendar dates to invent weekend price comparisons or revenue estimates.
""")
code("""con.execute('''SELECT month, listing_days, known_days, available_share, priced_days
FROM mart_calendar_month ORDER BY month''').df()""")
md("""## 5. Statistical results and sensitivity

Tests use one deterministic representative listing per host. Inspect sample sizes, effect sizes, confidence intervals and normality diagnostics in each result. Holm-adjusted primary p-values and trimmed-mean sensitivity p-values refer to different test families and estimands.
""")
code("""pd.DataFrame(results['hypotheses'])[[
    'id','status','p_holm','difference','cohens_d','ci95_low','ci95_high','trimmed_p_holm'
]]""")
md("""## 6. Evaluate before claiming model value

Group cross-validation stays within training hosts; the test split contains unseen hosts. Imputation and encoding are fitted within training folds. The median baseline wins this experiment; that is useful evidence against premature model deployment.
""")
code("""display(pd.DataFrame(results['models']['scores']))
print('Selected by training CV:', results['models']['selected_model'])
print('Host overlap:', results['models']['host_overlap'])
display(pd.DataFrame(results['models']['neighbourhood_errors']))
""")
code("display(Image(filename=str(OUT / 'figures/residuals.png'), width=850))")
md("""## 7. Make a reasoned next step

Add another dated snapshot and predeclare a temporal evaluation before experimenting with log-target or robust-loss models. Track changes in missingness, supply and price distributions. A model tuned repeatedly against this same holdout would need a new untouched validation set.

**Your exercise:** add a SQL query for room-type price coverage within each ward, explain its grain, and compare it to the explorer. Then document one engineering change you made independently.

Source: [Inside Airbnb](https://insideairbnb.com/get-the-data/), CC BY 4.0. See the repository AI disclosure and limitations before reusing these findings.
""")
code("con.close()")
notebook.cells=cells
notebook.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}}
target=root/'notebooks/01_market_walkthrough.ipynb'
target.parent.mkdir(parents=True,exist_ok=True)
nb.write(notebook,target)
print(target)
