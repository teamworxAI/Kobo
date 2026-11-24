# WEMA Study analytics dashboard

This dashboard analyses responses to the **WEMA Study** survey (Women's Experiences of Menstrual Disorders
Assessment, Kenya), collected with KoboToolbox at <https://ee.kobotoolbox.org/x/XkauKNnq/>. It is built for
physicians, funding partners and administrators. It shows the ten pre-specified table shells (T1–T10), the
pre-specified comparisons, adjusted models, a behavioural baseline and a data-quality report, and exports
everything to Excel.

It is a single Python app (Streamlit), with no database and no build step.

## What's inside

| Page | Content |
|---|---|
| Overview | Headline indicators with 95% CIs, key findings in plain language, burden by group, sample flow |
| T1–T10 | Each table shell with its breakdowns, charts, table view and CSV download |
| Comparisons | Diagnosed vs suspected · insured vs uninsured · HMB vs none · income · Nairobi vs other: differences with 95% CIs |
| Adjusted models | Firth logistic regression for care sought, hardship and diagnostic delay ≥3 years |
| Behavioural baseline | Q24–26 and Q86–87, described (not a Fogg model test) |
| What this sample can show | Precision, detectable differences and model capacity for the data now loaded; planning simulation at n = 200 / 400 / 800 with clustering by recruitment channel; calculator |
| Data quality | Item non-response by section (measured against the form's own skip logic), items over 10% missing, consistency checks |
| Methods & limitations | Populations, indicator definitions, statistical methods |
| Export | One Excel workbook with every table, plus the indicator dataset |

Analysis decisions are in [`docs/METHODS.md`](docs/METHODS.md). Problems found in the live form, and how the
analysis handles each one, are in [`docs/FORM_ISSUES.md`](docs/FORM_ISSUES.md). **Please read that file before
the next form deployment.**

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your Kobo token
streamlit run app.py
```

With no token, the app still opens. You can upload a Kobo export, or choose **Demo (synthetic data)** to look
around. Demo mode shows a warning banner on every page, because its numbers are made up.

### Connecting to KoboToolbox

1. In Kobo, go to **Account settings → Security → API key** and copy the token. Use an account that can *view
   submissions* for the form. A dedicated read-only account is best.
2. Put it in `.streamlit/secrets.toml` (or in environment variables):
   ```toml
   KOBO_TOKEN = "…"
   KOBO_SERVER = "https://kf.kobotoolbox.org"   # EU accounts: https://eu.kobotoolbox.org
   KOBO_ASSET_UID = "aLWbr2Y7epAUXji3GkuABi"
   APP_PASSWORD = "choose-a-strong-one"
   ```
3. The app pulls every submission through the Kobo API v2 and caches it for 15 minutes. **Refresh data** in the
   sidebar fetches it again straight away.

To work from a file instead, in Kobo go to **Data → Downloads**, choose *XLS*, set *Value and header format* to
**XML values and headers**, and upload the file. Label-format exports are converted back to codes automatically.

## Hosting

The app handles health data, so keep it private and always set `APP_PASSWORD`.

* **Streamlit Community Cloud** (free, simplest): push this repo, create an app from `app.py`, paste the secrets
  into *Settings → Secrets*, and under *Sharing* set the app to **private**, inviting only named viewers.
* **Docker** (any VM, Render, Railway, Azure App Service, etc.):
  ```bash
  docker build -t wema-dashboard .
  docker run -p 8501:8501 -e KOBO_TOKEN=… -e APP_PASSWORD=… wema-dashboard
  ```
  Put it behind HTTPS (most platforms do this for you).

## Sample size and power

`wema/power.py` simulates many studies at several sample sizes, condition mixes and amounts of clustering by
recruitment channel. It plants effects of known size and records how often the planned analyses recover them.
Results are cached in `wema/data/` and summarised in [`docs/SAMPLE_SIZE.md`](docs/SAMPLE_SIZE.md). After you
change the assumptions (for example, with pilot data), re-run:

```bash
python tools/run_power_sim.py
```

## Privacy safeguards built in

* The M-Pesa phone number is **dropped when the data loads**. It is never stored, shown or exported.
* Free-text comments are not displayed.
* Data is held only in memory and never written to disk. Exports contain derived indicators, not raw records.
* Groups under 40 are labelled *descriptive only*. Be careful publishing very small cells (n < 5).

## When the form changes

Choice codes and labels come from `wema/codebook.json`. After you redeploy the form, rebuild that file from the
live form (no token needed) and run the tests:

```bash
python tools/build_codebook.py
python -m pytest
```

`tests/test_codes.py` fails if a code the analysis depends on now means something else. If it fails, update
`wema/config.py` to match. New questions only need a line in `PROTOCOL_Q` in `tools/build_codebook.py` and,
if they should appear in a table, a block in `wema/report.py`.

## Project layout

```
app.py                  Streamlit UI (pages, filters, rendering)
wema/config.py          Kobo settings, answer codes, analysis constants
wema/codebook.json      Form definition (generated by tools/build_codebook.py)
wema/ingest.py          Kobo API / file import, clean-up, removal of identifying fields
wema/relevance.py       Re-applies the form's skip logic (for missing-data denominators)
wema/derive.py          Populations, groups and every derived indicator (with denominators)
wema/stats.py           Wilson / Newcombe CIs, chi-square / Fisher / Mann–Whitney, Firth regression
wema/tables.py          Table builders, comparisons, models, missing data, key findings
wema/report.py          The T1–T10 table shells (shared by the dashboard and the Excel export)
wema/charts.py          Plotly charts (colour-blind-safe palette, CI whiskers, small-n marking)
wema/export.py          Excel workbook
wema/demo.py            Synthetic data generator (demo and tests only)
tests/                  pytest suite
docs/                   Methods, form issues
```
