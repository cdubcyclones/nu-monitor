"""Centerpiece dashboard — 4 charts + 1 contextual Brazil overlay.

Implements the scope locked in docs/CENTERPIECE.md. Captions include the required
caveat language. Only two interactive controls (company selection + date range), per
the explicit out-of-scope list in CENTERPIECE.md § 5.

Run: streamlit run src/nu_monitor/app/dashboard.py
"""

from __future__ import annotations

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

# Streamlit invokes this file as a top-level script (no parent package), so the
# imports below must be ABSOLUTE. Relative `from ..config import ...` would raise
# `ImportError: attempted relative import with no known parent package` at runtime
# even though `pip install -e .` succeeds. This module is the only Streamlit
# entry point in the package; modules invoked only via `python -m nu_monitor`
# (e.g. __main__.py) keep package context and can keep relative imports.
from nu_monitor.config import DB_PATH
from nu_monitor.derive.metrics import cohort_snapshots, latest_deposits_pair, revenue_crossover

COHORT = ["NU", "SOFI", "SQ", "PYPL"]
COLORS = {"NU": "#9333EA", "SOFI": "#0EA5E9", "SQ": "#10B981", "PYPL": "#F59E0B"}


@st.cache_data
def load_panel() -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        df = con.execute("SELECT * FROM kpi_panel").df()
    df["period_end"] = pd.to_datetime(df["period_end"])
    return df


def _wide_rev_ni(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to one row per (company, period_end) with revenue + net_income + margin columns."""
    sub = df[(df["metric"].isin(["revenue", "net_income"])) & (df["definition_version"] == "v1")]
    w = (
        sub.pivot_table(index=["company", "period_end"], columns="metric", values="value", aggfunc="first")
        .reset_index()
        .dropna(subset=["revenue", "net_income"])
    )
    w["margin"] = (w["net_income"] / w["revenue"]) * 100.0
    return w


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="NU Comparative Fundamentals")
st.title("NU Comparative Fundamentals Monitor")

st.markdown(
    "**Locked question:** *Where does NU sit on the digital-banking cohort's "
    "growth-vs-profitability frontier, and what does its trajectory through that space "
    "look like relative to peers?*"
)
st.markdown(
    "Descriptive comparative read, not a tested relationship "
    "(see `docs/FINDINGS.md` for why the predictive track was retired). "
    "Methodology, definitional caveats, and the version-split metrics live in "
    "`docs/CENTERPIECE.md` and `docs/DATA_SOURCES.md`."
)

panel = load_panel()

with st.sidebar:
    st.markdown("**Controls**  (scope-locked; see CENTERPIECE § 5)")
    selected_companies = st.multiselect(
        "Companies", COHORT, default=COHORT,
        help="Filter the cohort panels (Charts 1–3). Chart 4 is NU vs SoFi only.",
    )
    dmin, dmax = panel["period_end"].min().date(), panel["period_end"].max().date()
    dr = st.date_input(
        "Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax,
        help="Limits the time x-axis on every chart.",
    )

if isinstance(dr, tuple) and len(dr) == 2:
    start_date, end_date = dr
else:
    start_date, end_date = dmin, dmax

mask = (panel["period_end"] >= pd.Timestamp(start_date)) & (panel["period_end"] <= pd.Timestamp(end_date))
cohort_df = panel[mask & panel["company"].isin(selected_companies)]
br_df = panel[mask & (panel["company"] == "BR_MACRO")]
color_scale = alt.Scale(domain=COHORT, range=[COLORS[c] for c in COHORT])

# ---------------------------------------------------------------------------
# Chart 1 — Revenue scale & trajectory (line, log-y)
# ---------------------------------------------------------------------------
st.header("Chart 1 — Revenue scale & trajectory")

rev_df = cohort_df[(cohort_df["metric"] == "revenue") & (cohort_df["definition_version"] == "v1")]

# Google-Finance-style hover readout: a selection that snaps to the nearest x-axis
# data point on mouseover, driving a vertical rule and one inline value label per
# company. Behavior is layered onto the existing styled line chart; styling, color
# scale, legend, axis labels, and caption are unchanged.
chart1_base = alt.Chart(rev_df).encode(
    x=alt.X("period_end:T", title="Quarter end", axis=alt.Axis(format="%Y Q%q")),
    y=alt.Y(
        "value:Q",
        scale=alt.Scale(type="log"),
        title="Quarterly revenue (US$M, log scale)",
        axis=alt.Axis(format=",.0f"),
    ),
    color=alt.Color("company:N", scale=color_scale, title="Company"),
)

chart1_lines = chart1_base.mark_line(point=True, strokeWidth=2).encode(
    tooltip=["company", "period_end:T",
             alt.Tooltip("value:Q", title="revenue ($M)", format=",.1f")],
)

chart1_nearest = alt.selection_point(
    nearest=True, on="mouseover", fields=["period_end"], empty=False,
)

# Transparent points layered across the chart capture the mouseover hit-tests.
chart1_selectors = (
    chart1_base.mark_point().encode(opacity=alt.value(0)).add_params(chart1_nearest)
)

# Vertical rule shown only at the selected x.
chart1_rule = (
    alt.Chart(rev_df)
    .mark_rule(color="#777", strokeDash=[3, 3])
    .encode(x="period_end:T")
    .transform_filter(chart1_nearest)
)

# Filled colored dots at the selected x for each company.
chart1_hover_pts = chart1_base.mark_point(
    filled=True, size=110, stroke="black", strokeWidth=1,
).encode(opacity=alt.condition(chart1_nearest, alt.value(1), alt.value(0)))

# Inline value labels colored to match each line. Stacked along y by line position
# (each label sits next to its own data point). Small dx pushes them right of the rule.
chart1_hover_labels = chart1_base.mark_text(
    align="left", dx=10, dy=-10, fontWeight="bold", fontSize=12,
).encode(
    text=alt.condition(chart1_nearest, alt.Text("value:Q", format=",.0f"), alt.value(" ")),
)

chart1 = (
    chart1_lines + chart1_selectors + chart1_rule + chart1_hover_pts + chart1_hover_labels
).properties(height=340)
st.altair_chart(chart1, use_container_width=True)
st.caption(
    "Quarterly total revenue, log y-axis. **Revenue definitions are not strictly "
    "identical** — IFRS (NU) vs US-GAAP (peers); SoFi reports total revenue *net of "
    "interest expense* (`RevenuesNetOfInterestExpense`); Block includes Bitcoin "
    "pass-through. Read for scale and slope, not precise levels."
)

# ---------------------------------------------------------------------------
# Chart 2 — Net margin trajectory
# ---------------------------------------------------------------------------
st.header("Chart 2 — Net margin trajectory")

margin_df = _wide_rev_ni(cohort_df)
chart2 = (
    alt.Chart(margin_df)
    .mark_line(point=True, strokeWidth=2)
    .encode(
        x=alt.X("period_end:T", title="Quarter end", axis=alt.Axis(format="%Y Q%q")),
        y=alt.Y("margin:Q", title="Net margin (net income / revenue, %)",
                axis=alt.Axis(format=".0f")),
        color=alt.Color("company:N", scale=color_scale, title="Company"),
        tooltip=["company", "period_end:T",
                 alt.Tooltip("revenue:Q", title="revenue ($M)", format=",.1f"),
                 alt.Tooltip("net_income:Q", title="net income ($M)", format=",.1f"),
                 alt.Tooltip("margin:Q", title="margin (%)", format=".1f")],
    )
    .properties(height=340)
)
zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#666", strokeDash=[4, 4]).encode(y="y:Q")
st.altair_chart(chart2 + zero, use_container_width=True)
st.caption(
    "Net margin = `net_income / revenue * 100`. **Cross-GAAP and cross-presentation "
    "differences** in the numerator and denominator persist (see Chart 1); a margin "
    "*level* is not strictly comparable across companies, but the *trajectory* and "
    "*direction* are robust. Dashed line marks zero margin (the profitability boundary)."
)

# ---------------------------------------------------------------------------
# Chart 3 — The frontier (revenue-vs-margin scatter with paths)
# ---------------------------------------------------------------------------
st.header("Chart 3 — The frontier (scale vs margin)")

# Primary: single log-x scatter+path. Most-recent dot enlarged & labeled per company.
front_df = margin_df.sort_values(["company", "period_end"]).copy()
last_per_co = front_df.groupby("company").tail(1)

base = alt.Chart(front_df).encode(
    x=alt.X(
        "revenue:Q",
        scale=alt.Scale(type="log"),
        title="Quarterly revenue (US$M, log scale)",
        axis=alt.Axis(format=",.0f"),
    ),
    y=alt.Y("margin:Q", title="Net margin (%)", axis=alt.Axis(format=".0f")),
    color=alt.Color("company:N", scale=color_scale, title="Company"),
)
path = base.mark_line(opacity=0.55, strokeWidth=2).encode(order="period_end:T")
points = base.mark_point(filled=True, size=55, opacity=0.85).encode(
    tooltip=["company", "period_end:T",
             alt.Tooltip("revenue:Q", title="revenue ($M)", format=",.1f"),
             alt.Tooltip("margin:Q", title="margin (%)", format=".1f")],
)
last_dot = alt.Chart(last_per_co).mark_point(
    filled=True, size=240, stroke="black", strokeWidth=1
).encode(
    x=alt.X("revenue:Q", scale=alt.Scale(type="log")),
    y="margin:Q",
    color=alt.Color("company:N", scale=color_scale),
)
last_label = alt.Chart(last_per_co).mark_text(align="left", dx=12, fontWeight="bold", fontSize=13).encode(
    x=alt.X("revenue:Q", scale=alt.Scale(type="log")),
    y="margin:Q",
    text="company:N",
    color=alt.Color("company:N", scale=color_scale),
)
zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#666", strokeDash=[4, 4]).encode(y="y:Q")

chart3_layered = (path + points + last_dot + last_label + zero_line).properties(height=440)
st.altair_chart(chart3_layered, use_container_width=True)
st.caption(
    "Each company's quarterly observations plotted in (revenue $M, net margin %) space, "
    "log-x; consecutive quarters connected to form the path-through-the-frontier. "
    "Larger labeled dot = most recent quarter per company. "
    "**Primary rendering** per CENTERPIECE § 2; small-multiples fallback would be triggered "
    "only if the single panel doesn't read clearly. **Falsification:** if NU's path "
    "overlaps a peer's at the same revenue scale rather than tracing a distinct arc, "
    "the centerpiece thesis fails — see CENTERPIECE § 1."
)

# ---------------------------------------------------------------------------
# Chart 4 — Deposits NU vs SoFi
# ---------------------------------------------------------------------------
st.header("Chart 4 — Deposits: NU vs SoFi (the cohort's deposit-funded peers)")

dep_df = panel[
    mask
    & (panel["metric"] == "deposits")
    & (panel["definition_version"] == "v1")
    & (panel["company"].isin(["NU", "SOFI"]))
]
pair_scale = alt.Scale(domain=["NU", "SOFI"], range=[COLORS["NU"], COLORS["SOFI"]])
chart4 = (
    alt.Chart(dep_df)
    .mark_line(point=True, strokeWidth=2)
    .encode(
        x=alt.X("period_end:T", title="Quarter end", axis=alt.Axis(format="%Y Q%q")),
        y=alt.Y("value:Q", title="Customer deposits (US$B)",
                axis=alt.Axis(format=",.0f")),
        color=alt.Color("company:N", scale=pair_scale, title="Company"),
        tooltip=["company", "period_end:T",
                 alt.Tooltip("value:Q", title="deposits ($B)", format=",.1f")],
    )
    .properties(height=340)
)
st.altair_chart(chart4, use_container_width=True)
st.caption(
    "Quarterly customer deposits, balance-sheet line. "
    "**Deposits are a directly comparable balance-sheet line**; Block and PayPal lack a "
    "meaningful customer-deposit equivalent and are correctly excluded — see "
    "DATA_SOURCES.md."
)

# ---------------------------------------------------------------------------
# Chart 5 — Brazil-context overlay (B, contextual only)
# ---------------------------------------------------------------------------
st.header("Chart 5 — NU credit quality in the Brazilian household credit cycle (contextual only)")

nu_npl_v1 = panel[
    (panel["company"] == "NU") & (panel["metric"] == "npl_15_90") & (panel["definition_version"] == "v1")
    & mask
].assign(series="NU NPL 15-90 (v1, Brazil-only)")
br_default = panel[(panel["company"] == "BR_MACRO") & (panel["metric"] == "household_default") & mask] \
    .assign(series="BR household default (BCB SGS 21084)")
br_selic = panel[(panel["company"] == "BR_MACRO") & (panel["metric"] == "selic_target") & mask] \
    .assign(series="Selic target (BCB SGS 432)")

overlay = pd.concat([
    nu_npl_v1[["period_end", "value", "series"]],
    br_default[["period_end", "value", "series"]],
    br_selic[["period_end", "value", "series"]],
])
overlay_colors = {
    "NU NPL 15-90 (v1, Brazil-only)": "#9333EA",
    "BR household default (BCB SGS 21084)": "#0EA5E9",
    "Selic target (BCB SGS 432)": "#6B7280",
}
chart5 = (
    alt.Chart(overlay)
    .mark_line(point=True, strokeWidth=2)
    .encode(
        x=alt.X("period_end:T", title="Quarter end", axis=alt.Axis(format="%Y Q%q")),
        y=alt.Y("value:Q", title="Percent", axis=alt.Axis(format=".0f")),
        color=alt.Color(
            "series:N",
            scale=alt.Scale(domain=list(overlay_colors), range=list(overlay_colors.values())),
            title="Series",
            legend=alt.Legend(orient="bottom", direction="vertical", labelLimit=400),
        ),
        tooltip=["series", "period_end:T", alt.Tooltip("value:Q", format=".2f")],
    )
    .properties(height=360)
)
st.altair_chart(chart5, use_container_width=True)
st.caption(
    "**Contextual only.** NU's NPL series shown here is the original (v1) \"Brazilian "
    "Consumer Credit Portfolio\" definition; only three same-definition observations "
    "are available (Q3'24, Q2'25, Q3'25). **No statistical relationship between NU's "
    "credit metric and Brazilian system-wide indicators is claimed — three points "
    "cannot establish one.** This panel exists to make explicit *where* NU operates, "
    "not to test a claim about how NU tracks the cycle."
)

# ---------------------------------------------------------------------------
# C — credibility back-matter
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("Methodology & data integrity (C back-matter)")
st.markdown(
    """
1. **Heterogeneous ingestion in one schema.** Three different parser paths reconciled
   into one `kpi_panel`: NU 6-K hidden-text releases (foreign-issuer KPI exhibits, no
   XBRL); NU IFRS financial-statement HTML tables (backfill); peer XBRL company-facts
   (calendar-quarter `frames`); BCB SGS REST. See `docs/DATA_SOURCES.md`.
2. **The Q4'25 column-format change in NU releases**, and the "current-quarter-column-0
   only" defense that makes layout drift a non-event.
3. **`definition_version` versioning.** `efficiency_ratio` v1↔v2 and
   `npl_15_90` / `npl_90_plus` v1 (Brazil-only) ↔ v2 (consolidated). The dashboard's
   Brazil overlay uses NU NPL v1 only; NPL/efficiency are absent from cross-company
   charts because they are *comparison-unsafe*.
4. **Managerial vs statutory revenue (Q4'25+).** ~3.5% gap on revenue (4,685.9 IFRS vs
   4,857.3 managerial at Q4'25); net income identical under both. We make IFRS statutory
   the canonical `revenue`; the ingest order enforces the choice.
5. **IFRS Q4 derivation (full year − nine month).** Exact arithmetic on two reported
   IFRS figures, cross-validated against the Q4'25 earnings-release net income
   ($894.8M match).
6. **Per-filer XBRL choices.** SoFi `RevenuesNetOfInterestExpense` vs Block / PayPal
   `Revenues`; deposits only for SoFi.
7. **The Q4'22 hole.** Both the release and the financial-statements exhibit fail for
   that single quarter; see `docs/DATA_SOURCES.md § Q4'22`.
8. **Descriptive, not predictive.** See `docs/FINDINGS.md § 1`.
9. **BCB API quirks.** 406 on bare URL and on explicit `Accept: application/json`;
   `dataInicial=01/01/2021` is the working bound.
"""
)


# ---------------------------------------------------------------------------
# Tail: computed numerical claims (also shown in the README narrative)
# ---------------------------------------------------------------------------
with st.expander("Numerical claims used in the README narrative (computed from this panel)"):
    st.caption(
        "`margin_first_pct` / `margin_last_pct` / `margin_delta_pp` are bookend values, "
        "meaningful for monotonic trajectories (NU, SOFI, PYPL on this panel). For volatile "
        "series — Block here — the bookends do not characterize the path; read Chart 2's "
        "line and the SQ subsection in docs/DATA_SOURCES.md."
    )
    snaps = cohort_snapshots()
    st.write({
        s.company: {
            "window": f"{s.first_period} → {s.last_period} ({s.years:.2f} y, {s.quarters} q)",
            "revenue_first_$M": round(s.revenue_first_m, 1),
            "revenue_last_$M": round(s.revenue_last_m, 1),
            "revenue_CAGR_%/yr": round(s.revenue_cagr_pct, 1),
            "margin_first_%": None if s.margin_first_pct is None else round(s.margin_first_pct, 1),
            "margin_first_quarter": str(s.margin_first_period),
            "margin_last_%": None if s.margin_last_pct is None else round(s.margin_last_pct, 1),
            "margin_delta_pp": None if s.margin_delta_pp is None else round(s.margin_delta_pp, 1),
            "first_profit_quarter": str(s.first_profit_quarter),
        }
        for s in snaps
    })
    dp = latest_deposits_pair()
    st.write({
        "NU vs SoFi deposits at the latest common quarter": {
            "quarter": str(dp.quarter),
            "NU_$B": dp.nu_deposits_b, "SoFi_$B": dp.sofi_deposits_b,
            "ratio_NU_over_SoFi": round(dp.ratio_nu_over_sofi, 2),
        },
        "Revenue crossovers": {
            "NU surpasses SoFi": str(revenue_crossover("NU", "SOFI")),
            "NU surpasses Block": str(revenue_crossover("NU", "SQ")),
            "NU surpasses PayPal": str(revenue_crossover("NU", "PYPL")),
        },
    })
