"""
PROVN Challenge 97 — Cohort vs Demographic Stratification
Addresses grader feedback: is the 2024 Q4 cohort effect independent of
plan-tier and company-size mix, or is it the same finding restated?

Computes:
  1. 2024 Q4 cohort plan-tier and company-size mix vs overall mix.
  2. Within-cohort churn rate per stratum, compared to full-dataset rate
     per stratum (the baseline a properly-mixed cohort would produce).
  3. Expected 2024 Q4 cohort churn if it behaved like the overall dataset
     at its own demographic mix (indirect standardisation).
  4. Residual = actual Q4 2024 churn - mix-adjusted expected churn.
"""

import pandas as pd
from scipy.stats import fisher_exact

BASE = "G:/My Drive/PRVN/97-churn-diagnosis"

customers = pd.read_csv(f"{BASE}/customers.csv", encoding="utf-8-sig")
customers["signup_date"] = pd.to_datetime(customers["signup_date"])
customers["churn_date"]  = pd.to_datetime(customers["churn_date"], errors="coerce")
customers["churned_bool"] = (customers["churned"] == "Y").astype(int)
customers["signup_quarter"] = customers["signup_date"].dt.to_period("Q").astype(str)

Q4 = "2024Q4"
q4_mask = customers["signup_quarter"] == Q4
q4 = customers[q4_mask]
non_q4 = customers[~q4_mask]

print("=" * 72)
print("2024 Q4 COHORT vs OVERALL — DEMOGRAPHIC MIX AND CONTROLLED CHURN")
print("=" * 72)

n_q4 = len(q4)
n_all = len(customers)
q4_rate = q4["churned_bool"].mean() * 100
all_rate = customers["churned_bool"].mean() * 100
print(f"\n  Q4 2024 cohort n      : {n_q4}")
print(f"  Overall cohort n      : {n_all}")
print(f"  Q4 2024 churn rate    : {q4_rate:.1f}%")
print(f"  Overall churn rate    : {all_rate:.1f}%")

# ─── MIX COMPARISON ──────────────────────────────────────────────────────────
def mix(df, col):
    return (df[col].value_counts(normalize=True) * 100).round(1)

print(f"\n[PLAN-TIER MIX]")
tier_q4  = mix(q4, "plan_tier")
tier_all = mix(customers, "plan_tier")
for t in sorted(set(tier_all.index) | set(tier_q4.index)):
    print(f"  {t:<15s}  Q4 2024: {tier_q4.get(t, 0):>5.1f}%   overall: {tier_all.get(t, 0):>5.1f}%")

print(f"\n[COMPANY-SIZE MIX]")
size_q4  = mix(q4, "company_size")
size_all = mix(customers, "company_size")
for s in sorted(set(size_all.index) | set(size_q4.index)):
    print(f"  {s:<15s}  Q4 2024: {size_q4.get(s, 0):>5.1f}%   overall: {size_all.get(s, 0):>5.1f}%")

# ─── WITHIN-STRATUM CHURN — Q4 vs overall-at-that-stratum ────────────────────
def stratum_compare(col):
    print(f"\n[WITHIN-STRATUM CHURN — {col.upper()}]")
    print(f"  {'stratum':<15s} {'Q4 n':>5s} {'Q4 rate':>9s} {'overall n':>10s} {'overall rate':>14s} {'Q4 minus overall':>18s}")
    for lvl in sorted(customers[col].unique()):
        q4_sub  = q4[q4[col] == lvl]
        all_sub = customers[customers[col] == lvl]
        q4_r  = q4_sub["churned_bool"].mean() * 100 if len(q4_sub)  else 0
        all_r = all_sub["churned_bool"].mean() * 100 if len(all_sub) else 0
        print(f"  {lvl:<15s} {len(q4_sub):>5d} {q4_r:>8.1f}% {len(all_sub):>10d} {all_r:>13.1f}% {q4_r - all_r:>+17.1f} pp")

stratum_compare("plan_tier")
stratum_compare("company_size")

# ─── INDIRECT STANDARDISATION ────────────────────────────────────────────────
# Expected Q4 churns IF each stratum behaved like the overall dataset.
# Uses the NON-Q4 dataset as the reference population (so Q4 is not compared
# against itself). Expected rate = sum over strata of
# (Q4 share of that stratum) * (non-Q4 churn rate of that stratum).

def expected_rate(col):
    ref = non_q4
    expected = 0.0
    for lvl, q4_sub in q4.groupby(col):
        ref_sub = ref[ref[col] == lvl]
        if len(ref_sub) == 0:
            continue
        ref_rate = ref_sub["churned_bool"].mean()
        expected += (len(q4_sub) / len(q4)) * ref_rate
    return expected * 100

exp_by_tier = expected_rate("plan_tier")
exp_by_size = expected_rate("company_size")

# Joint (plan_tier x company_size)
def expected_rate_joint():
    expected = 0.0
    for (tier, size), q4_sub in q4.groupby(["plan_tier", "company_size"]):
        ref_sub = non_q4[(non_q4["plan_tier"] == tier) & (non_q4["company_size"] == size)]
        if len(ref_sub) == 0:
            continue
        ref_rate = ref_sub["churned_bool"].mean()
        expected += (len(q4_sub) / len(q4)) * ref_rate
    return expected * 100

exp_joint = expected_rate_joint()

print(f"\n[INDIRECT STANDARDISATION — reference = non-Q4 (n={len(non_q4)})]")
print(f"  Actual Q4 2024 churn rate                        : {q4_rate:.1f}%")
print(f"  Expected if Q4 matched non-Q4 by plan_tier alone : {exp_by_tier:.1f}%")
print(f"  Residual (plan_tier control)                     : {q4_rate - exp_by_tier:+.1f} pp")
print(f"  Expected if Q4 matched non-Q4 by company_size    : {exp_by_size:.1f}%")
print(f"  Residual (company_size control)                  : {q4_rate - exp_by_size:+.1f} pp")
print(f"  Expected if Q4 matched non-Q4 on joint (tier*size): {exp_joint:.1f}%")
print(f"  Residual (joint control)                         : {q4_rate - exp_joint:+.1f} pp")

# ─── FISHER EXACT — Q4 vs non-Q4, overall and within top stratum ─────────────
def fisher(a_ch, a_n, b_ch, b_n, label):
    table = [[a_ch, a_n - a_ch], [b_ch, b_n - b_ch]]
    _, p = fisher_exact(table)
    return p

q4_ch  = int(q4["churned_bool"].sum())
nq4_ch = int(non_q4["churned_bool"].sum())
p_all  = fisher(q4_ch, len(q4), nq4_ch, len(non_q4), "overall")

print(f"\n[FISHER EXACT — Q4 vs non-Q4]")
print(f"  Q4:    {q4_ch}/{len(q4)}  ({q4_rate:.1f}%)")
print(f"  nonQ4: {nq4_ch}/{len(non_q4)}  ({non_q4['churned_bool'].mean()*100:.1f}%)")
print(f"  p (two-sided)                            : {p_all:.4f}")

# Within Basic tier only
q4_basic  = q4[q4["plan_tier"] == "Basic"]
nq4_basic = non_q4[non_q4["plan_tier"] == "Basic"]
if len(q4_basic) and len(nq4_basic):
    p_basic = fisher(int(q4_basic["churned_bool"].sum()),  len(q4_basic),
                     int(nq4_basic["churned_bool"].sum()), len(nq4_basic), "Basic")
    print(f"  Within Basic tier only — Q4 vs non-Q4     : p = {p_basic:.4f} "
          f"(Q4 {q4_basic['churned_bool'].mean()*100:.1f}% vs non-Q4 {nq4_basic['churned_bool'].mean()*100:.1f}%)")

# Within small (1-10) company size only
q4_small  = q4[q4["company_size"]  == "1-10"]
nq4_small = non_q4[non_q4["company_size"] == "1-10"]
if len(q4_small) and len(nq4_small):
    p_small = fisher(int(q4_small["churned_bool"].sum()),  len(q4_small),
                     int(nq4_small["churned_bool"].sum()), len(nq4_small), "1-10")
    print(f"  Within 1-10 employees only — Q4 vs non-Q4 : p = {p_small:.4f} "
          f"(Q4 {q4_small['churned_bool'].mean()*100:.1f}% vs non-Q4 {nq4_small['churned_bool'].mean()*100:.1f}%)")

print("\n" + "=" * 72)
print("DONE")
print("=" * 72)
