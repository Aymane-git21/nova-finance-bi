# Start here — what's left, in order

Everything else in this repo is reference material. **This file is the only one you need to follow.**

---

## Where the project actually stands

**Done and verified — you don't need to touch any of it:**

- 1.1 M-line synthetic dataset, 103 tests
- HANA model: 31 views, a SQLScript table function, 35 cross-checks proving the SQL matches an independent Python implementation
- OData V4 service (CAP)
- Live dashboard: **https://aymane-git21.github.io/nova-finance-bi/**
- ABAP CDS stack (authored, labelled not-activated), 106 checks
- Performance and eco-design work, measured
- All the documentation: backlog, golden rules, BI roadmap, change management, GDPR, ADRs

**That is already a strong portfolio.** If you sent it today it would stand up.

**Two things are left, and both are yours because they need a browser and a microphone:**

| # | Task | Time | Why it matters |
|---|---|---|---|
| **A** | Build the SAC story | 3–5 h | SAC is a named requirement. Right now the README honestly says you haven't demonstrated it |
| **B** | Record the walkthrough video | 1–2 h | This is what you attach to an application |

**Do A before B**, so the video can include SAC.

If you only have time for one: **do B**. A video of what already exists is worth more than an SAC story nobody watches.

---

# TASK A — SAC

## A0. What SAC even is (5 min read)

SAP Analytics Cloud is a website. You upload data, describe what the columns mean, then drag things onto a canvas to make charts. That's it.

Three words you need:

| Word | Means |
|---|---|
| **Model** | Your uploaded data *plus* a description of what each column is. Upload a CSV, tell SAC "this column is a date, this one is money" — that's a model. |
| **Dimension** | A column you slice *by*. Entity, programme, period. Text-ish things. |
| **Measure** | A column you add up. Amounts, counts. Numbers you'd sum. |
| **Story** | The report. Pages of charts built on a model. |

The whole job: **upload 4 files → make 4 models → make 1 story with 3 pages.**

One thing that trips everyone: **SAC guesses which columns are measures and guesses wrong.** It sees `fiscal_year` = 2025 and thinks "number, must be a measure" and tries to add years together. You'll fix a few of these by hand. That's normal and I've listed exactly which ones.

## A1. Log in (10 min)

You registered on 25 July. Find the welcome email from SAP — subject line mentions SAP Analytics Cloud — and use the link in it to set your password if you haven't.

- [ ] Logged in, can see the SAC home page

**⚠️ Before you go further — set a calendar reminder now, for 12 August 2026: "Extend SAC trial".**

Your trial ends **24 August**. Around day 20 SAC offers to extend it to 90 days total (to 23 October). Miss that window and you lose 60 days. Set it now, it takes 20 seconds.

- [ ] Calendar reminder set for 12 August

## A2. Upload the first file and make a model (30 min)

Start with the smallest file so you learn the flow on something quick.

The files are on your machine at:
```
C:\Users\ayman\Desktop\nova-finance-bi\sac\extracts\
```

**Do this:**

1. In SAC's left menu find **Modeler** (may be under "Browse" or a grid icon).
2. Choose to create a new model **from a CSV / from a file**.
3. Upload **`sac_pl_actuals.csv`** (1,296 rows — small and fast).
4. SAC shows you a preview with each column and a guessed type. **This screen is the whole job.** Set them:

| Column | Set it to | Note |
|---|---|---|
| `company_code` | Dimension | |
| `company_name` | Dimension | |
| `fiscal_year` | **Dimension** | ⚠️ SAC will guess Measure. Change it |
| `fiscal_period` | **Dimension** | ⚠️ Same |
| `period_date` | **Date** | ⚠️ Most important. Granularity **Month**. Without this you get no time axis |
| `fiscal_period_label` | Dimension | |
| `pl_section` | Dimension | |
| `account_group` | Dimension | |
| `account_group_name` | Dimension | |
| `amount_group_currency` | **Measure** | Currency EUR |
| `line_count` | Measure | |
| `manual_line_count` | Measure | |

5. Name it **NS_PL_Actuals** and save.

- [ ] `NS_PL_Actuals` model created

**If you get stuck:** the exact menu names change between SAC versions. What you're looking for is "create a model from a file". If you can't find it, take a screenshot of what you're seeing and send it to me — I'll tell you where to click.

## A3. Make your first chart (30 min)

This is the payoff. You'll see the story appear in the data.

1. Left menu → **Stories** → new story → **Canvas** (a blank page you drop charts onto).
2. Add a **Chart**. Pick your `NS_PL_Actuals` model.
3. Set it up:
   - Chart type: **Bar**
   - **Measure**: `amount_group_currency`
   - **Dimension**: `company_code`
4. You should see four bars, one per entity.

- [ ] First chart works

Now the good one:

5. Add another chart. Type: **Line**.
   - **Measure**: `amount_group_currency`
   - **Dimension** (the x-axis): **`fiscal_period_label`** — *not* `period_date`, see below
   - **Colour / series**: `pl_section`

You should get separate lines for revenue and each cost category across three and a half years.

> ### ⚠️ Use `fiscal_period_label` on chart axes, not `period_date`
>
> `period_date` is a **Date** dimension, and SAC date dimensions have a built-in
> hierarchy: All → Year → Quarter → Month. Dropped straight onto an axis it
> defaults to the **top** of that hierarchy, so every period collapses into a
> single bar labelled `(all)`. It looks broken and the data is perfectly fine.
>
> `fiscal_period_label` is plain text — `2023-01`, `2023-02` — with no hierarchy
> to fight, and it is zero-padded so it sorts correctly. It exists in the
> extracts for precisely this.
>
> **Keep `period_date` in the model.** It is what gives you time filters,
> year-over-year and period ranges later. It is just an awkward first axis.

> ### ⚠️ A negative total is correct, not a bug
>
> The grand total across everything is **−126,774,552.51**. Revenue is stored
> as a negative number and costs as positive — the standard sign convention,
> applied once in the model so nothing downstream has to re-derive it. So the
> total is €3,295 m of revenue against €3,168 m of cost: the group's profit
> over three and a half years.
>
> This is also why a chart of *everything* is unhelpful. Split by `pl_section`,
> or filter to `COST_OF_SALES`, and it becomes readable immediately.

- [ ] Trend chart works
- [ ] **Screenshot both** → save into `sac/screenshots/`

**Stop here if you're short on time.** One model and two charts already means you've used SAC. Everything after this makes it better, not real.

## A4. The other two analytic models (45 min)

Same flow as A2. Two files:

**`sac_programme_costs.csv`** → name it `NS_Programme_Costs`

Same column rules, plus one trap:

> `total_budget_eur` — set aggregation to **MIN**, not SUM.
> It's the programme's total budget repeated on every row. Summing it across 42 periods gives you a number 42× too big. (This is a classic mistake and knowing to avoid it is worth mentioning in an interview.)

**`sac_close_tasks.csv`** → name it `NS_Close_Monitor`

Two traps here:

> `days_to_close` — aggregation **AVERAGE**, not SUM. Adding up "days to close" across periods is meaningless.
>
> `actual_completion_date` — **one row is blank. Leave it blank.** If SAC offers to fill empty values with 0, say no. That period is genuinely still open, and showing it as a zero-day close would be the most misleading number in the whole project.

- [ ] `NS_Programme_Costs` created
- [ ] `NS_Close_Monitor` created

## A5. Build the three story pages (1–1.5 h)

Back in your story, make three pages. Keep each page to one question.

### Page 1 — "CFO overview"

| Add | Type | Settings |
|---|---|---|
| Days to close | Bar chart | Measure `days_to_close` (AVERAGE), dimension `company_code`, **filter `task_id` = T12**, sort descending |
| P&L trend | Line chart | The one you already built in A3 |
| Manual share | Numeric point | Measure `manual_line_count` ÷ `line_count` if SAC lets you; otherwise just show `manual_line_count` |

**The bar chart sorted descending is the whole page.** One entity is visibly taller than the other three. That's NS30, and that's the finding.

### Page 2 — "Programme controlling"

| Add | Type | Settings |
|---|---|---|
| Cost by programme | Bar chart | `programme_name` × `amount_group_currency`, descending |
| Burn over time | Line chart | X = `period_date`, colour = `programme_name`, **filter to 5 programmes** |

Ten lines is unreadable. Five is a chart.

### Page 3 — "Close monitor"

| Add | Type | Settings |
|---|---|---|
| Days to close over time | Line chart | X = `period_date`, colour = `company_code`, filter `task_id` = T12 |
| Task delays | Table | Rows `company_code`, columns `task_name`, measure `delay_working_days` (AVERAGE) |

**The line chart is the best thing in the whole SAC story.** One entity's line sits above the others for three straight years. If that doesn't jump out at you, something's set wrong — tell me.

- [ ] Three pages built
- [ ] **Screenshot every page**

### Check your numbers

These must match. If they don't, something's misconfigured:

| Check | Should be |
|---|---|
| NS30 average days to close | **8.17** |
| NS10 / NS20 / NS40 | **5.1 – 5.4** |

**If NS30 shows ~5 instead of 8.17:** either aggregation is SUM instead of AVERAGE, or the `task_id = T12` filter is missing. Those two cause nearly every problem.

- [ ] Numbers check out

## A6. Planning model — the BPC evidence (1 h) — optional but valuable

This is what lets you answer "experience on BPC projects". Skip it if you're running out of time; the rest still stands.

1. New model from **`sac_budget_actual.csv`**. Set the model type to **Planning** (not Analytic).
2. Column setup as before, and then **the one step that matters:**

> **Map the `version` column to SAC's built-in Version dimension**, not a normal dimension.
>
> SAC planning models have a Version dimension already built in, with categories: Actual, Budget, Forecast. Your file's three values map straight onto them.
>
> **This mapping is exactly what BPC calls a "Category".** If you import `version` as an ordinary dimension the model still loads, but every planning feature quietly stops working. It's also a likely interview question, so it's worth the extra two minutes.

3. Then demo three things and screenshot each:
   - **Type a number** into a Forecast cell and publish it
   - **Copy Actual → Forecast** (this is the most-used function in any real planning system)
   - **A variance table**: rows = programme, columns = Version, showing Actual vs Budget

- [ ] Planning model created with Version mapped correctly
- [ ] Three screenshots

## A7. Tell me you're done

Put every screenshot in `sac/screenshots/`, then message me.

**I'll then rewrite the three places that currently say you haven't demonstrated SAC** — the README requirements table, `docs/sac-and-bpc.md`, and ADR-004. I'm deliberately not changing them until the screenshots exist.

---

# TASK B — The video

## B0. What you're making

An **8-minute screen recording** with you talking over it. No webcam, no editing, no music. You click through things and explain them.

The full script is in [`docs/walkthrough-script.md`](docs/walkthrough-script.md) — it has the actual words to say, shot by shot. **You don't have to memorise it.** Have it open on a second screen or on your phone and read it.

## B1. How to record (10 min setup)

**Simplest option — already on your PC, no install:**

1. Press **Win + G** → the Xbox Game Bar opens
2. Find the **Capture** widget → click the microphone icon so it's ON
3. Click the record button (or just press **Win + Alt + R**)
4. Press **Win + Alt + R** again to stop
5. Files land in `Videos\Captures`

**Better option if you want more control:** OBS Studio (free, obsproject.com). Add a "Display Capture" source and an "Audio Input" for your mic. More setup, better result.

Either is fine. Game Bar is genuinely good enough.

- [ ] Test-record 20 seconds and play it back. **Check you can hear yourself.**

## B2. Before you hit record

- [ ] Start Docker Desktop, then in a terminal:
  ```bash
  ./hana/hxe.sh start
  ```
- [ ] In a second terminal:
  ```bash
  cd cap && npx cds serve --port 4004
  ```
- [ ] Open these tabs/windows ready to switch between:
  - The live dashboard (hard-refresh it: **Ctrl+Shift+R**)
  - VS Code with the repo open
  - A terminal
  - Your SAC story, if you did Task A
- [ ] Close Slack, mail, Discord, notifications
- [ ] Do **one silent practice run** — just click through the order without talking. It makes take two dramatically better.

## B3. Record it

Follow [`docs/walkthrough-script.md`](docs/walkthrough-script.md) top to bottom.

**It does not need to be perfect.** If you fumble a sentence, pause, and say it again — nobody minds, and it's better than 15 takes.

**If 8 minutes feels like too much:** the script marks a **3-minute cut** at the bottom. Do that instead. A tight 3 minutes beats a rambling 8.

- [ ] Recorded
- [ ] Watched it back once

## B4. Publish it

1. Upload to YouTube
2. Set visibility to **Unlisted** (not Private — nobody can see Private, not even with the link)
3. Copy the link
4. Send it to me and I'll put it in the README

- [ ] Uploaded, unlisted, link sent

---

# If you get stuck

Tell me:
- **which step number** you're on
- **what you see** (a screenshot is ideal)

Don't spend 40 minutes hunting for a menu. SAC's UI changes between releases and I'd rather redirect you in one message.

---

# The order, one more time

1. ⏰ **Calendar reminder, 12 August** — 20 seconds, do it now
2. **A1–A3** — log in, one model, two charts (~1 h). Stop here and you've already used SAC
3. **A4–A5** — the other models and the three pages (~2 h)
4. **A6** — planning model (~1 h, optional)
5. **A7** — send me the screenshots
6. **B** — record the video (~1–2 h)
7. Send me the YouTube link

**After that the project is finished.**
