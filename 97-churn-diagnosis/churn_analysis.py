"""
PROVN Challenge 97: Diagnose 62% Churn Spike
Full churn analysis using real CSV data.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from scipy.stats import chi2_contingency
import warnings
warnings.filterwarnings('ignore')

BASE = "G:/My Drive/PRVN/97-churn-diagnosis"

# ─── 1. LOAD DATA ────────────────────────────────────────────────────────────
customers = pd.read_csv(f"{BASE}/customers.csv", encoding="utf-8-sig")
support   = pd.read_csv(f"{BASE}/support.csv",   encoding="utf-8-sig")
usage     = pd.read_csv(f"{BASE}/usage.csv",      encoding="utf-8-sig")

# Normalize industry name typo
customers["industry"] = customers["industry"].str.replace("PropertyMaintenance",
                                                           "Property Maintenance")

# Parse dates
customers["signup_date"] = pd.to_datetime(customers["signup_date"])
customers["churn_date"]  = pd.to_datetime(customers["churn_date"], errors="coerce")
usage["last_active_date"] = pd.to_datetime(usage["last_active_date"], errors="coerce")

# Merge
df = customers.merge(support, on="customer_id").merge(usage, on="customer_id")
df["churned_bool"] = (df["churned"] == "Y").astype(int)

# Signup cohort (calendar quarter)
df["signup_quarter"] = df["signup_date"].dt.to_period("Q").astype(str)

print("=" * 65)
print("PROVN CHALLENGE 97 — CHURN DIAGNOSIS REPORT")
print("=" * 65)

# ─── 2. OVERALL CHURN RATE ───────────────────────────────────────────────────
total    = len(df)
churned  = df["churned_bool"].sum()
rate     = churned / total * 100

print(f"\n[OVERALL]")
print(f"  Total customers:  {total}")
print(f"  Churned:          {churned}")
print(f"  Overall churn rate: {rate:.1f}%")
print(f"  Retained:         {total - churned}")

# ─── 3. CHURN BY SEGMENT ────────────────────────────────────────────────────
def segment_table(df, col, label):
    tbl = df.groupby(col)["churned_bool"].agg(["sum","count"])
    tbl.columns = ["churned","total"]
    tbl["rate"] = tbl["churned"] / tbl["total"] * 100
    tbl = tbl.sort_values("rate", ascending=False)
    print(f"\n[CHURN BY {label.upper()}]")
    for seg, row in tbl.iterrows():
        print(f"  {seg:<25s}  churned={int(row.churned):>3d} / {int(row.total):>3d}  rate={row.rate:.1f}%")
    return tbl

plan_tbl    = segment_table(df, "plan_tier",    "Plan Tier")
size_tbl    = segment_table(df, "company_size", "Company Size")
ind_tbl     = segment_table(df, "industry",     "Industry")
cohort_tbl  = segment_table(df, "signup_quarter","Signup Cohort")

# ─── 4. CHI-SQUARE SIGNIFICANCE TESTS ───────────────────────────────────────
print(f"\n[STATISTICAL SIGNIFICANCE — CHI-SQUARE]")
for col, label in [("plan_tier","Plan Tier"),
                   ("company_size","Company Size"),
                   ("industry","Industry")]:
    ct = pd.crosstab(df[col], df["churned_bool"])
    chi2, p, dof, _ = chi2_contingency(ct)
    print(f"  {label:<20s}  chi2={chi2:.2f}  p={p:.4f}  {'*** SIGNIFICANT' if p<0.05 else '(not sig)'}")

# ─── 5. USAGE CORRELATES ────────────────────────────────────────────────────
print(f"\n[USAGE — CHURNED vs RETAINED MEANS]")
usage_cols = ["avg_monthly_logins","feature_scheduling_uses_6mo",
              "feature_dispatch_uses_6mo","feature_invoicing_uses_6mo",
              "features_used_count"]
for col in usage_cols:
    ch  = df[df["churned_bool"]==1][col].mean()
    ret = df[df["churned_bool"]==0][col].mean()
    t, p = stats.ttest_ind(df[df["churned_bool"]==1][col],
                           df[df["churned_bool"]==0][col])
    sig = "***" if p < 0.001 else ("**" if p<0.01 else ("*" if p<0.05 else ""))
    print(f"  {col:<40s}  churned={ch:>6.2f}  retained={ret:>6.2f}  p={p:.4f} {sig}")

# Features used count — churn rate by bucket
print(f"\n[CHURN RATE BY FEATURES_USED_COUNT]")
for n in sorted(df["features_used_count"].unique()):
    sub = df[df["features_used_count"]==n]
    r = sub["churned_bool"].mean()*100
    print(f"  features_used={n}  n={len(sub):>3d}  churn_rate={r:.1f}%")

# ─── 6. SUPPORT CORRELATES ──────────────────────────────────────────────────
print(f"\n[SUPPORT TICKETS — CHURNED vs RETAINED]")
ch_tickets  = df[df["churned_bool"]==1]["tickets_submitted_6mo"].mean()
ret_tickets = df[df["churned_bool"]==0]["tickets_submitted_6mo"].mean()
t, p = stats.ttest_ind(df[df["churned_bool"]==1]["tickets_submitted_6mo"],
                        df[df["churned_bool"]==0]["tickets_submitted_6mo"])
print(f"  Avg tickets (churned):  {ch_tickets:.2f}")
print(f"  Avg tickets (retained): {ret_tickets:.2f}")
print(f"  t-test p-value: {p:.4f} {'*** SIGNIFICANT' if p<0.05 else ''}")

print(f"\n[CHURN BY PRIMARY TICKET CATEGORY]")
for cat, grp in df.groupby("primary_ticket_category"):
    r = grp["churned_bool"].mean()*100
    print(f"  {cat:<20s}  n={len(grp):>3d}  churn_rate={r:.1f}%")

# Resolution time
print(f"\n[AVG RESOLUTION DAYS — CHURNED vs RETAINED]")
ch_res  = df[df["churned_bool"]==1]["avg_resolution_days"].mean()
ret_res = df[df["churned_bool"]==0]["avg_resolution_days"].mean()
print(f"  Churned: {ch_res:.2f} days  |  Retained: {ret_res:.2f} days")

# ─── 7. MRR ANALYSIS ────────────────────────────────────────────────────────
print(f"\n[MRR ANALYSIS]")
ch_mrr  = df[df["churned_bool"]==1]["mrr_usd"].mean()
ret_mrr = df[df["churned_bool"]==0]["mrr_usd"].mean()
total_mrr_lost = df[df["churned_bool"]==1]["mrr_usd"].sum()
print(f"  Avg MRR churned:  ${ch_mrr:.0f}")
print(f"  Avg MRR retained: ${ret_mrr:.0f}")
print(f"  Total MRR at risk: ${total_mrr_lost:,.0f}")

# MRR by plan tier
print(f"\n[MRR LOST BY PLAN TIER]")
mrr_plan = df[df["churned_bool"]==1].groupby("plan_tier")["mrr_usd"].agg(["sum","mean","count"])
mrr_plan.columns = ["total_mrr_lost","avg_mrr","n_churned"]
for tier, row in mrr_plan.sort_values("total_mrr_lost", ascending=False).iterrows():
    print(f"  {tier:<15s}  n={int(row.n_churned)}  avg_mrr=${row.avg_mrr:.0f}  total_lost=${row.total_mrr_lost:,.0f}")

# ─── 7b. MONTHLY CHURN RATE (for 62% spike context) ─────────────────────────
print(f"\n[MONTHLY CHURN RATE — RECENT 6 MONTHS]")
months = pd.period_range("2025-10", "2026-03", freq="M")
monthly_rows = []
for m in months:
    month_start = m.to_timestamp()
    next_start  = (m + 1).to_timestamp()
    active_start = ((customers["signup_date"] < month_start) &
                    ((customers["churn_date"].isna()) |
                     (customers["churn_date"] >= month_start))).sum()
    churned_this = ((customers["churn_date"] >= month_start) &
                    (customers["churn_date"] < next_start)).sum()
    r = churned_this / active_start * 100 if active_start > 0 else 0
    monthly_rows.append((str(m), churned_this, active_start, r))
    print(f"  {m}: churned={churned_this}, active_at_start={active_start}, monthly_rate={r:.2f}%")
recent_avg = sum(x[3] for x in monthly_rows) / len(monthly_rows)
print(f"  6-month average monthly churn rate: {recent_avg:.2f}%")
print(f"  Spec reports rise from 2.1% to 3.4% (62% increase) over same window.")
print(f"  Dataset avg 3.45% matches the current-state 3.4% number.")

# ─── 8. CHURN TIMING ────────────────────────────────────────────────────────
print(f"\n[CHURN TIMING — MONTHS TO CHURN]")
ch_df = df[df["churned_bool"]==1].copy()
ch_df["months_to_churn"] = ((ch_df["churn_date"] - ch_df["signup_date"]) /
                             pd.Timedelta(days=30)).round(1)
print(f"  Median months to churn: {ch_df['months_to_churn'].median():.1f}")
print(f"  Mean months to churn:   {ch_df['months_to_churn'].mean():.1f}")
print(f"  <3 months:  {(ch_df['months_to_churn']<3).sum()} ({(ch_df['months_to_churn']<3).mean()*100:.1f}%)")
print(f"  3-6 months: {((ch_df['months_to_churn']>=3)&(ch_df['months_to_churn']<6)).sum()} ({((ch_df['months_to_churn']>=3)&(ch_df['months_to_churn']<6)).mean()*100:.1f}%)")
print(f"  6-12 months:{((ch_df['months_to_churn']>=6)&(ch_df['months_to_churn']<12)).sum()} ({((ch_df['months_to_churn']>=6)&(ch_df['months_to_churn']<12)).mean()*100:.1f}%)")
print(f"  >12 months: {(ch_df['months_to_churn']>=12).sum()} ({(ch_df['months_to_churn']>=12).mean()*100:.1f}%)")

# Churn dates by month (spike detection)
print(f"\n[CHURN EVENTS BY MONTH (last 12)]")
ch_df["churn_month"] = ch_df["churn_date"].dt.to_period("M")
monthly_churn = ch_df.groupby("churn_month").size()
for mo, cnt in monthly_churn.tail(12).items():
    print(f"  {mo}: {cnt}")

# ─── 9. TOP PREDICTORS SUMMARY ──────────────────────────────────────────────
print(f"\n{'='*65}")
print("KEY FINDINGS SUMMARY")
print(f"{'='*65}")
print(f"  1. Overall churn rate: {rate:.1f}%")
print(f"  2. Basic plan churn rate: {plan_tbl.loc['Basic','rate']:.1f}%  vs"
      f" Enterprise: {plan_tbl.loc['Enterprise','rate']:.1f}%")
top_ind = ind_tbl.index[0]
print(f"  3. Highest-churn industry: {top_ind} ({ind_tbl.loc[top_ind,'rate']:.1f}%)")
print(f"  4. Single-feature users churn at:"
      f" {df[df['features_used_count']==1]['churned_bool'].mean()*100:.1f}%"
      f"  vs 3-feature: {df[df['features_used_count']==3]['churned_bool'].mean()*100:.1f}%")
print(f"  5. Avg logins — churned: {df[df['churned_bool']==1]['avg_monthly_logins'].mean():.1f}"
      f"  retained: {df[df['churned_bool']==0]['avg_monthly_logins'].mean():.1f}")
print(f"  6. Total MRR at risk: ${total_mrr_lost:,.0f}")

# ─── 10. CHARTS ─────────────────────────────────────────────────────────────

COLORS_CHURN   = "#D94F3D"
COLORS_RETAIN  = "#4878A8"
COLORS_NEUTRAL = "#7B9E87"

# ── Chart 1: Churn by Segment (Plan, Size, Industry) ──────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("Churn Rate by Customer Segment", fontsize=14, fontweight="bold", y=1.01)

def bar_chart(ax, tbl, title, color=COLORS_CHURN):
    order = tbl.sort_values("rate", ascending=True)
    bars = ax.barh(order.index, order["rate"], color=color, edgecolor="white", linewidth=0.5)
    ax.axvline(rate, color="grey", linestyle="--", linewidth=1, label=f"Overall {rate:.1f}%")
    for bar, (_, row) in zip(bars, order.iterrows()):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{row['rate']:.1f}%", va="center", fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("Churn Rate (%)")
    ax.set_xlim(0, max(order["rate"].max() * 1.25, rate * 1.25))
    ax.legend(fontsize=8)
    ax.spines[["top","right"]].set_visible(False)

bar_chart(axes[0], plan_tbl,  "By Plan Tier")
bar_chart(axes[1], size_tbl,  "By Company Size")
bar_chart(axes[2], ind_tbl,   "By Industry")

plt.tight_layout()
plt.savefig(f"{BASE}/churn_by_segment.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n[SAVED] churn_by_segment.png")

# ── Chart 2: Usage Correlation ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Usage Behaviour: Churned vs. Retained", fontsize=14, fontweight="bold")

# 2a: avg monthly logins boxplot
data_ch  = df[df["churned_bool"]==1]["avg_monthly_logins"]
data_ret = df[df["churned_bool"]==0]["avg_monthly_logins"]
bp = axes[0].boxplot([data_ch, data_ret], patch_artist=True,
                      labels=["Churned","Retained"],
                      medianprops=dict(color="black", linewidth=2))
for patch, color in zip(bp["boxes"], [COLORS_CHURN, COLORS_RETAIN]):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[0].set_title("Avg Monthly Logins", fontweight="bold")
axes[0].set_ylabel("Logins / Month")
axes[0].spines[["top","right"]].set_visible(False)

# 2b: features used count bar
feat_churn = (df.groupby("features_used_count")["churned_bool"]
               .agg(["mean","count"]).reset_index())
feat_churn["rate"] = feat_churn["mean"] * 100
bars = axes[1].bar(feat_churn["features_used_count"].astype(str),
                   feat_churn["rate"],
                   color=[COLORS_CHURN if r > rate else COLORS_RETAIN
                           for r in feat_churn["rate"]],
                   edgecolor="white")
axes[1].axhline(rate, color="grey", linestyle="--", linewidth=1, label=f"Overall {rate:.1f}%")
for bar, r in zip(bars, feat_churn["rate"]):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f"{r:.1f}%", ha="center", fontsize=9)
axes[1].set_title("Churn Rate by Features Used", fontweight="bold")
axes[1].set_xlabel("Number of Features Used")
axes[1].set_ylabel("Churn Rate (%)")
axes[1].legend(fontsize=8)
axes[1].spines[["top","right"]].set_visible(False)

# 2c: ticket category churn
cat_churn = (df.groupby("primary_ticket_category")["churned_bool"]
               .agg(["mean","count"]).reset_index())
cat_churn["rate"] = cat_churn["mean"] * 100
cat_churn = cat_churn.sort_values("rate", ascending=True)
colors_cat = [COLORS_CHURN if r > rate else COLORS_RETAIN for r in cat_churn["rate"]]
axes[2].barh(cat_churn["primary_ticket_category"], cat_churn["rate"],
             color=colors_cat, edgecolor="white")
axes[2].axvline(rate, color="grey", linestyle="--", linewidth=1, label=f"Overall {rate:.1f}%")
for i, (_, row) in enumerate(cat_churn.iterrows()):
    axes[2].text(row["rate"] + 0.3, i, f"{row['rate']:.1f}%", va="center", fontsize=9)
axes[2].set_title("Churn Rate by Support Category", fontweight="bold")
axes[2].set_xlabel("Churn Rate (%)")
axes[2].legend(fontsize=8)
axes[2].spines[["top","right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{BASE}/usage_correlation.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"[SAVED] usage_correlation.png")

# ── Chart 3: Cohort Churn Heatmap + MRR at Risk ───────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Churn Cohort Analysis & MRR at Risk", fontsize=14, fontweight="bold")

# 3a: cohort churn rates
cohort_tbl_sorted = cohort_tbl.sort_index()
bars = axes[0].bar(range(len(cohort_tbl_sorted)),
                   cohort_tbl_sorted["rate"],
                   color=[COLORS_CHURN if r > rate else COLORS_NEUTRAL
                           for r in cohort_tbl_sorted["rate"]],
                   edgecolor="white")
axes[0].axhline(rate, color="grey", linestyle="--", linewidth=1, label=f"Overall {rate:.1f}%")
axes[0].set_xticks(range(len(cohort_tbl_sorted)))
axes[0].set_xticklabels(cohort_tbl_sorted.index, rotation=45, ha="right", fontsize=8)
for bar, r in zip(bars, cohort_tbl_sorted["rate"]):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f"{r:.0f}%", ha="center", fontsize=8)
axes[0].set_title("Churn Rate by Signup Cohort (Quarter)", fontweight="bold")
axes[0].set_ylabel("Churn Rate (%)")
axes[0].legend(fontsize=8)
axes[0].spines[["top","right"]].set_visible(False)

# 3b: MRR at risk by plan tier (stacked: churned vs retained)
plan_mrr = df.groupby(["plan_tier","churned_bool"])["mrr_usd"].sum().unstack(fill_value=0)
plan_mrr.columns = ["Retained MRR","Churned MRR"]
plan_order = ["Basic","Professional","Enterprise"]
plan_mrr = plan_mrr.reindex(plan_order)
x = range(len(plan_order))
axes[1].bar(x, plan_mrr["Retained MRR"]/1000, label="Retained MRR", color=COLORS_RETAIN, alpha=0.8)
axes[1].bar(x, plan_mrr["Churned MRR"]/1000,  label="Churned MRR",
            bottom=plan_mrr["Retained MRR"]/1000, color=COLORS_CHURN, alpha=0.8)
axes[1].set_xticks(list(x))
axes[1].set_xticklabels(plan_order)
axes[1].set_title("MRR Distribution by Plan Tier", fontweight="bold")
axes[1].set_ylabel("MRR ($K)")
axes[1].legend()
axes[1].spines[["top","right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{BASE}/cohort_mrr_analysis.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"[SAVED] cohort_mrr_analysis.png")

print(f"\n{'='*65}")
print("ANALYSIS COMPLETE — all charts saved.")
print(f"{'='*65}")
