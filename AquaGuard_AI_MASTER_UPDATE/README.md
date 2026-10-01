# AquaGuard AI 💧
**Smart Water Monitoring & Leak Intelligence — Hackathon MVP**

> MVP • Simulated Data. AquaGuard AI does **not** connect to any real household
> meter, sensor, or live utility system. All analysis in this prototype runs
> on the provided Stage-1 simulated CSV files.

---

## 1. Project Purpose

AquaGuard AI is a smart household and residential-building water monitoring
system. It analyzes water-consumption data, learns each household's own
normal behavior, identifies unusual consumption, flags **possible** hidden
leaks, and tells legitimate high water usage (guests, cleaning, laundry
days...) apart from genuinely unexplained abnormal usage.

### The Problem
Fixed, one-size-fits-all consumption thresholds produce constant false
alarms: a 6-person household's normal Friday usage looks like an "anomaly"
to a threshold tuned for a 2-person household, and a single unusual day
(guests, a big cleaning session) looks identical to the start of a real
leak if you don't look at persistence and corroborating evidence.

### The Solution
AquaGuard builds a **Consumption Fingerprint** for every household,
individually, from that household's own history — normal range, weekday
pattern, learned idle period, expected night flow — and only escalates a
status when the evidence (persistence, night-flow evidence, building-level
evidence) actually supports it. A single abnormal day is never enough on
its own to declare a leak.

---

## 2. Main Features

| Page | What it does |
|---|---|
| **Overview** | Automatic, KPI-card summary the moment a household is selected: status, consumption, baseline, trend, idle flow, leak indicator. |
| **Household Monitoring** | Time-series charts (7/30/90 days / full history) of consumption vs. the household's own normal band, plus a night/idle-flow chart. |
| **Consumption Fingerprint** | The full learned profile: normal min/max, average/median, weekday pattern, typical high/low days, learned idle period, expected idle flow, confidence, observation count. |
| **Leak Detection** | Dedicated evidence view: an evidence checklist, the night-flow history chart, and a "Possible hidden leak" (never "confirmed") verdict. |
| **Building Water Balance** | `Unaccounted Water = Main Meter − Apartment Total − Legitimate External Use`, classified as Balanced / Isolated / Repeated / Persistent. |
| **Tank & Pump** | Cross-checks tank level, pump state and building-level unaccounted water to flag a *possible* float/overflow or abnormal pump condition. |
| **Data Explorer** | Filter/search the raw simulated records; shows the live record count. |
| **AI Insights** | Natural-language "Why? / What does this mean? / Recommended action" summary built from the household's own computed numbers (never invented). |
| **AI Assistant** | A chat box that answers questions about the *currently selected* household only, using a deterministic local engine, optionally rephrased by an LLM if an API key is configured. |
| **Smart Form** | When AquaGuard sees an unusual, unexplained day, it asks a short multiple-choice question instead of asking the user to type in consumption numbers. |
| **Demo Mode** | Jumps to a real record in the dataset that matches a named scenario (Normal / High Legitimate Usage / Possible Hidden Leak / Building Imbalance / Tank-Pump Anomaly). Never fabricates a scenario that isn't actually in the data. |
| **Bilingual (EN/AR)** | Language chosen on first launch; all labels and AI explanations follow it. The analysis itself never changes with language. |

---

## 3. Architecture

```
DATA SOURCE  →  ANALYSIS ENGINE  →  DASHBOARD / AI
(Stage-1 CSVs)   (modules/*.py)      (app.py + modules/ui.py)
```

This separation is intentional: Stage 2 can swap the simulated CSVs for a
real sensor/API feed without changing a single line of the analysis logic —
only `modules/data_loader.py` would need a new source.

```
aquaguard/
├── app.py                     # Streamlit entry point, page router, sidebar
├── requirements.txt
├── README.md
├── .streamlit/
│   ├── config.toml            # dark/cyan theme
│   └── secrets.toml.example   # copy to secrets.toml for optional AI phrasing
├── data/
│   ├── apartment_timeseries.csv     # 4x/day readings per apartment
│   ├── household_profiles.csv       # apartment/building/members/appliances
│   └── building_meter_tank.csv      # daily building meter/tank/pump data
└── modules/
    ├── data_loader.py         # robust column-mapping + caching data loader
    ├── fingerprint.py         # household-specific Consumption Fingerprint
    ├── anomaly_detection.py   # transparent rule-based status engine
    ├── leak_detection.py      # leak-evidence view (reuses the same engine)
    ├── building_balance.py    # Building Water Balance analysis
    ├── tank_pump.py           # Tank & Pump protection analysis
    ├── smart_forms.py         # session-based legitimate-use explanations
    ├── ai_insights.py         # deterministic NL insights + optional LLM
    └── ui.py                  # theme, translations, shared components
```

---

## 4. Data Flow & Files Used

- **`household_profiles.csv`** (`AquaGuard_Household_Profiles_Stage1_RAW`) —
  one row per apartment: `Apartment_ID, Building_ID, Household_Members,
  Water_Using_Appliances`. Drives the sidebar's Building/Apartment picker
  and the "Household Members" KPI.
- **`apartment_timeseries.csv`** (`AquaGuard_Apartment_TimeSeries_Stage1_RAW`) —
  4 readings/day (Night, Workday, Afternoon, Evening) per apartment, with
  `Water_Consumption_Liters`, `Night_Flow_2AM_5AM_Liters` and
  `Idle_Time_Flow_Liters`. Aggregated to one row per apartment/day by
  `data_loader.get_apartment_daily()` and is the core input to the
  Consumption Fingerprint and the leak-detection engine.
- **`building_meter_tank.csv`** (`AquaGuard_Building_Meter_Tank_Stage1_RAW`) —
  one row per building/day: `Apartment_Meters_Total_Liters,
  Legitimate_External_Use_Liters, Unaccounted_Water_Liters,
  Main_Meter_Liters, Tank_Level_Percent, Pump_State`. Drives Building Water
  Balance and Tank & Pump.

All three are loaded through `data_loader.load_all_data()`, which maps
whatever column names actually appear in the files onto the canonical names
the analysis engine expects (case/spacing-insensitive alias matching). If a
file or a required column is missing, the app shows a clear notice and
disables only the dependent feature — it never invents a value.

---

## 5. How the Consumption Fingerprint Works

The fingerprint is **not** one global threshold. For each apartment:

1. The **first 7 days** of its history are treated as an initial warm-up
   baseline (assumed representative, since nothing abnormal has been
   confirmed yet).
2. From day 8 onward, AquaGuard walks forward **day by day**. Each new day
   is compared against the fingerprint learned *so far*:
   - If it looks normal (or the user explained it via the Smart Form), it's
     folded into the learned baseline.
   - If it looks abnormal, it's **excluded** from the baseline.
3. This means a persistent, unexplained anomaly (like a leak that runs for
   two weeks) never drags the household's own definition of "normal" up to
   meet it — which a plain running median/mean would do.
4. Robust statistics (median + MAD, and the 10th/90th percentile band) are
   used throughout so that occasional legitimate spikes don't distort the
   baseline either.
5. A **weekday-specific** pattern (median/mean per weekday, computed from
   the learned-normal pool) lets AquaGuard tell a household's normal Friday
   or Saturday spike apart from a real anomaly on any other day.
6. Trend (Increasing / Stable / Decreasing) compares the most recent window
   of readings against the window before it.
7. **Expected idle flow** is learned the same incremental way from
   `Night_Flow_2AM_5AM_Liters`, so a leak that keeps that value elevated for
   most of the dataset cannot poison its own detection threshold.

---

## 6. How Leak Detection Works

The Leak Detection page reuses the exact same status engine as Overview
(single source of truth — `modules/anomaly_detection.py`) and adds the
night-flow evidence trail:

- **Persistence**: consecutive recent days flagged high *and unexplained*.
- **Night-flow evidence**: how many of the last 7 nights sit far above the
  household's own learned expected idle flow.
- Three+ abnormal nights out of the last 7 → **"Possible hidden leak"**.
- The internal severity scale (L1–L8, described in the provided operations
  file) drives the public status but is never shown to the user as a raw
  table — only the four public statuses (Normal / Monitoring / Warning /
  Critical) and the underlying reasons are shown.
- AquaGuard **never** states a confirmed leak — only "possible", consistent
  with the fact that this is simulated data, not a live physical sensor.

---

## 7. How Smart Forms Work

When the status engine sees an abnormal, *unexplained* high day, the
Overview / Household Monitoring / Leak Detection pages show a short
multiple-choice question ("Was there any unusual water-use activity during
this period?") instead of asking the user to type in a number. The chosen
explanation is stored in `st.session_state` for that apartment+date. If the
explanation is one of the legitimate options, it is folded back into that
household's fingerprint (see §5, step 2) and the status is recalculated
immediately — the app never claims the answer proves or disproves a
physical leak, it only marks that day as explained.

---

## 8. How Building Water Balance Works

```
Unaccounted_Water = Main_Meter − Apartment_Meters_Total − Legitimate_External_Use
```

The provided data already includes a computed `Unaccounted_Water_Liters`
column; `modules/building_balance.py` also recomputes it independently as a
consistency check. The imbalance is classified using the building's own
typical apartment total (5% of it, floor 50 L) as the "meaningful"
threshold, then:

- **Balanced** — no meaningful imbalance recently.
- **Isolated** — imbalance seen on 1–2 of the last 14 days.
- **Repeated** — 2+ consecutive imbalanced days, but not the majority.
- **Persistent** — a majority of the last 14 days imbalanced (escalates to
  **Critical** if the trend is also increasing).

Only "Repeated" / "Persistent" trigger the
**"Possible external/shared-pipe water loss"** message — a single-day
imbalance is not treated as proof of anything.

---

## 9. How Tank & Pump Protection Works

`modules/tank_pump.py` never diagnoses a broken component from one signal
alone. It looks for the *combination* of: tank level near-full (≥95%), the
pump running `Continuous` rather than cycling, and the building already
showing unexplained unaccounted water. Only when multiple signals line up
does it report **"Possible tank/float issue"** or **"Possible abnormal pump
operation"** — always phrased as "possible" / "suspected".

---

## 10. Running Locally

```bash
cd aquaguard
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. No database or external service
is required — everything runs off the CSVs in `data/`.

### Optional: AI-improved phrasing
The app works fully without any API key (a deterministic local explanation
engine powers both the AI Insights page and the AI Assistant chat). To
optionally let a configured Claude model improve the *wording* of answers:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml and paste a real ANTHROPIC_API_KEY
```

`.streamlit/secrets.toml` is git-ignored and is never displayed in the UI.
If the key is missing, invalid, or the request fails for any reason, the
app silently falls back to the deterministic answer — it never breaks.

---

## 11. Deploying to Streamlit Community Cloud

1. Push this project to a GitHub repository (see §12).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at your repo, branch, and `app.py` as the entry point.
3. (Optional) In the app's **Settings → Secrets**, paste the same
   `ANTHROPIC_API_KEY = "..."` line to enable AI-improved phrasing in the
   deployed app.
4. Deploy. No other configuration is required — `requirements.txt` and
   `.streamlit/config.toml` are already in place.

---

## 12. Preparing for GitHub

```bash
cd aquaguard
git init
git add .
git commit -m "AquaGuard AI — MVP prototype"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

`.gitignore` already excludes `.streamlit/secrets.toml` and Python cache
files, so no credentials will be committed.

---

## 13. Important Notes on Simulated Data

- This MVP uses **only** the three provided Stage-1 CSV files. Nothing is
  fabricated: where a required column or file is missing, the affected
  feature is disabled with a clear message rather than showing invented
  numbers.
- The dataset spans **2026-09-01 to 2026-09-20** across **3 buildings** and
  **11 apartments** (880 timestamped readings + 61 building/day rows).
- Apartment **102** contains the dataset's simulated hidden-leak scenario
  (persistently elevated night flow from 2026-09-06 onward) and is the best
  apartment to select to see the Leak Detection page in action.
- Building **1** shows a real building-level imbalance / continuous-pump
  event on 2026-09-16–17, useful for exercising the Building Water Balance
  and Tank & Pump pages.
- **Stage 2** (out of scope for this MVP) would replace only
  `modules/data_loader.py`'s file-reading with a real sensor/API feed — the
  analysis engine (`fingerprint.py`, `anomaly_detection.py`,
  `building_balance.py`, `tank_pump.py`) is designed to need no changes.
