#!/usr/bin/env python3
"""Check the figures of the manuscript against the regenerated report.

Values are read from the report with regular expressions. Each check then looks
in the manuscript for the sentence fragment or table row that carries the value,
written as the manuscript prints it, so that a value is found only in the place
where it is meant. Runs of spaces are ignored on both sides.

    python3 -I check_paper_numbers.py REPORT.md PAPER.tex

The account of the lost requests and of the baseline builds that ran over their
time limit is checked against data/lost_requests.csv and
data/time_limit_events.csv, which list them from the run logs. Not covered
(taken from the run logs, the label files or the verification notes, as
Section 4.8 of the paper states): the build times and the counts of the records
labelled last.
"""
import csv
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from math import comb

rep = open(sys.argv[1], encoding="utf-8").read()
tex = open(sys.argv[2], encoding="utf-8").read()
N_BUGS = 388


def norm(s):
    return re.sub(r"[ \t]+", " ", s)


texn = norm(tex)
ok = bad = 0


def R(pattern, text=None, flags=0):
    m = re.search(pattern, rep if text is None else text, flags)
    if not m:
        sys.exit(f"report: pattern not found: {pattern}")
    return m.groups() if m.groups() else m.group(0)


def T(desc, expected):
    """expected is the literal text that the manuscript must contain."""
    global ok, bad
    if norm(expected) in texn:
        ok += 1
    else:
        bad += 1
        print(f"MISSING  {desc}\n         {expected}")


def C(desc, cond):
    """a relation that a sentence of the manuscript states in words"""
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
        print(f"FALSE    {desc}")


def fig_source(label):
    """the source of the figure that carries this label, so that the plotted values are
    checked where they are plotted, whatever the colours and line styles"""
    end = tex.index("\\label{" + label + "}")
    return norm(tex[tex.rindex("\\begin{figure}", 0, end):end])


def th(n):          # 1330 -> 1{,}330
    return f"{int(n):,}".replace(",", "{,}")


def exact_p(x, y):
    """exact two-sided McNemar p-value for x against y discordant pairs"""
    x, y = int(x), int(y)
    n = x + y
    k = min(x, y)
    return min(Fraction(1), 2 * Fraction(sum(comb(n, i) for i in range(k + 1)), 2 ** n))


def fmt(v, nd=2):
    """round half up to nd decimals (v: Fraction or number)"""
    d = Decimal(v.numerator) / Decimal(v.denominator) if isinstance(v, Fraction) else Decimal(str(v))
    return str(d.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def mp(x, y, nd=2):
    return fmt(exact_p(x, y), nd)


def pt(x, y):       # p-value in a table: three decimals, or <0.001
    v = exact_p(x, y)
    return "$<$0.001" if v < Fraction(1, 2000) else fmt(v, 3)


def pct(a, b, nd=1):
    return fmt(Fraction(100 * int(a), int(b)), nd)


def holm(ps):
    """Holm-adjusted values, in the order given"""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out = [None] * len(ps)
    run = Fraction(0)
    for rank, i in enumerate(order):
        run = max(run, min(Fraction(1), (len(ps) - rank) * ps[i]))
        out[i] = run
    return out


def power(n, d, alpha=Fraction(5, 100)):
    """power of the exact two-sided McNemar test, conditional on n discordant pairs, for a true difference d"""
    rej = [k for k in range(n + 1) if exact_p(k, n - k) <= alpha]
    px = Fraction(n + d, 2 * n)
    return sum(comb(n, k) * px ** k * (1 - px) ** (n - k) for k in rej)


ARMS = ("full", "binary_only", "no_judge")
MACRO = {"full": r"\cfull{}", "binary_only": r"\cbin{}", "no_judge": r"\cnoj{}"}

WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
WORDS_CAP = {k_: v_.capitalize() for k_, v_ in WORDS.items()}

# ── headline ──────────────────────────────────────────────────────────────
arms = {}
for arm in ARMS:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+)% \| (\d+) \|")
    arms[arm] = dict(pl=int(g[0]), acc=int(g[1]), co=int(g[2]), dc=int(g[3]), pend=int(g[4]), prec=g[5], ov=int(g[6]))
F, BO, NJ = (arms[a] for a in ARMS)
C("no pending label", all(a["pend"] == 0 for a in arms.values()))
C("every bug evaluable", R(r"evaluable in all three arms \(the paired set\): \*\*(\d+)\*\*")[0] == str(N_BUGS))
it = re.findall(r"\| (\d) \| (\d+) \| ([\d.]+)% \| ([\d.]+)% \| (\d+) \| ([\d.]+)% \|", rep)
assert len(it) == 4
first_share = pct(it[0][1], F["pl"], 0)
PRICE_IN, PRICE_OUT = Fraction(30, 100), Fraction(250, 100)       # USD per million input and output tokens
pr18 = R(r"at USD ([\d.]+) per million input tokens and USD ([\d.]+) per million output tokens")
C("the report used the list prices that the paper states", (Fraction(pr18[0]), Fraction(pr18[1])) == (PRICE_IN, PRICE_OUT))
T("prices stated in the paper", r"0.30 United States dollars (USD) per million input tokens and 2.50 per million output tokens~\citep{google2026pricing}")
lp18 = {}                                                          # section 18, one row per configuration and two for the control
for name in list(ARMS) + ["control, as run", "control, early stop"]:
    g = R(rf"\| {re.escape(name)} \| ([\d,]+) \| ([\d,]+) \| ([\d.]+)% \| \$([\d.]+) \| \$([\d.]+) \| \$([\d.]+) \| ([\d.]+)% \| \$([\d.]+) \| \$([\d.]+) \| \$([\d.]+) \| \$([\d.]+) \|")
    tin, tout = int(g[0].replace(",", "")), int(g[1].replace(",", ""))
    lp18[name] = dict(tin=tin, tout=tout, usd=(tin * PRICE_IN + tout * PRICE_OUT) / 10 ** 6, repair=g[4], judge=g[5], jshare=g[6], flat=g[10])
    C(f"cost of {name} at list prices follows from its tokens", fmt(lp18[name]["usd"]) == g[3])
pb18 = {a: R(rf"- {a}: per bug, mean \$([\d.]+), median \$([\d.]+), maximum \$([\d.]+)") for a in ARMS}
cost = {}
for arm in ARMS:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| ([\d,]+) \| \$([\d.]+) \| \$([\d.]+) \| \$([\d.]+) \| \$([\d.]+) \| \$([\d.]+) \| (\d+) \| ([\d.]+) \|")
    tok = int(g[2].replace(",", ""))
    usd = lp18[arm]["usd"]
    C(f"flat-rate estimate of {arm}, as the harness logged it", fmt(Fraction(tok * 35, 10 ** 8)) == g[3] == lp18[arm]["flat"])
    C(f"input and output tokens of {arm} add up to its total", lp18[arm]["tin"] + lp18[arm]["tout"] == tok)
    cost[arm] = dict(cand=int(g[0]), calls=int(g[1]), tok=tok, usd=fmt(usd), mean=fmt(usd / N_BUGS, 3), med=fmt(pb18[arm][1], 3), mx=fmt(pb18[arm][2], 3),
                     pl=fmt(usd / arms[arm]["pl"], 3), fix=fmt(usd / arms[arm]["co"], 3), s=g[8], h=g[9], judge=lp18[arm]["judge"], repair=lp18[arm]["repair"])
    C(f"mean cost per bug of {arm}, as the report gives it", fmt(usd / N_BUGS, 4) == pb18[arm][0])
CF = cost["full"]
st = {}
for arm in ARMS[1:]:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+) \| (\d+) \| (\d+) \| ([\d.]+) \|")
    st[arm] = dict(x=int(g[0]), y=int(g[1]), xp=int(g[6]), yp=int(g[7]), xd=int(g[10]), yd=int(g[11]))
hs = dict(zip(ARMS[1:], holm([exact_p(st[a]["x"], st[a]["y"]) for a in ARMS[1:]])))
for a in ARMS[1:]:
    C(f"Holm value of {a}: the two comparisons with Full, as the report gives it", fmt(hs[a], 4) == R(rf"\| {a} \| \d+ \| \d+ \| \d+ \| [\d.]+ \| [\d.]+ \| ([\d.]+) \|")[0])
T("Holm: the family", r"the two pairwise tests on the primary metric form one family and are adjusted with Holm's procedure~\citep{holm1979}.")
T("Holm: the family, in the caption of the ablation table", r"Holm adjusts the two-sided tests on the primary metric over the two comparisons (Section~\ref{sec:design})")
d_bo, d_nj = F["co"] - BO["co"], F["co"] - NJ["co"]
b, j = st["binary_only"], st["no_judge"]

T("abstract: headline", rf"it produces {F['pl']} plausible patches, {first_share}\% of them at the first attempt, of which {F['co']} are labelled correct under an LLM-assisted protocol with author adjudication ({pct(F['co'], N_BUGS)}\% of the bugs; precision {F['prec']}\%), at an estimated repair-run API cost of \${CF['mean']} per bug")
T("abstract: test evidence", rf"the correct fixes fall from {F['co']} to {BO['co']} (McNemar p~=~{mp(b['x'], b['y'], 3)}, Holm-adjusted {fmt(hs['binary_only'], 3)})")
T("abstract: Judge", rf"Removing the Judge leaves {NJ['co']} (p~=~{mp(j['x'], j['y'])}) at half the cost, and four independent attempts")
T("contribution 2", rf"{F['pl']} plausible and {F['co']} verified-correct patches (precision {F['prec']}\%) on the {N_BUGS} active \dfj{{}} v1.2 bugs, with at most four tested candidates per bug, at an estimated repair-run API cost of \${CF['mean']} per bug")
T("contribution 3", rf"three configurations paired on {N_BUGS} bugs, an equal-budget resampling control and a replication analysis of first attempts show that withholding the test output costs {d_bo} correct fixes, the only difference that survives multiplicity correction, ")
T("RQ1 sentence", rf"On the {N_BUGS} bugs, \svarp{{}} produces {F['pl']} plausible patches ({pct(F['pl'], N_BUGS)}\%), of which {F['co']} are verified correct ({pct(F['co'], N_BUGS)}\%). Its precision, the share of plausible patches that are correct, is {F['prec']}\% ({F['co']}/{F['pl']}); the {F['ov']} remaining patches are overfitting")
split = R(r"full arm label split: \{'Correct \(alternative\)': (\d+), 'Correct \(equivalent\)': (\d+), 'Correct \(identical\)': (\d+), 'Overfitting': (\d+)\}")
ovp = R(r"full arm, overfitting per project: Chart (\d+), Closure (\d+), Lang (\d+), Math (\d+), Mockito (\d+), Time (\d+)")
T("overfitting per project", rf"(Chart {ovp[0]}, Closure {ovp[1]}, Lang {ovp[2]}, Math {ovp[3]}, Mockito {ovp[4]}, Time {ovp[5]})")
T("discussion: precision of Full", rf"In the \cfull{{}} configuration {F['prec']}\% of the test-passing patches are labelled correct")
T("discussion: overfitting patches", rf"The {F['ov']} overfitting patches are concentrated")
T("RQ1 answer", rf"\svarp{{}} repairs {F['co']} of the {N_BUGS} active \dfj{{}} v1.2 bugs ({pct(F['co'], N_BUGS)}\%), with {F['prec']}\% of its test-passing patches verified correct. The counts")
T("conclusion: headline", rf"\svarp{{}} repairs {F['co']} of the {N_BUGS} active \dfj{{}} v1.2 bugs ({pct(F['co'], N_BUGS)}\%); {first_share}\% of its {F['pl']} test-passing patches are found at the first attempt and {F['prec']}\% of them are verified correct, at an estimated repair-run API cost of \${CF['mean']} per bug")
T("comparison with ReinFix", rf"and ReinFix (GPT-4o) {F['co'] - 146} fewer.")
T("comparison with VibeRepair", rf"VibeRepair (GPT-4o) reports {WORDS[abs(F['co'] - 174)]} correct fix{'es' if abs(F['co'] - 174) > 1 else ''} {'fewer' if F['co'] > 174 else 'more'} than ours")
precs = [float(arms[a]["prec"]) for a in ARMS[1:]] + [float(R(r"control precision: ([\d.]+)%")[0])]
T("discussion: precision range", rf"the reduced configurations and the control lie between {int(min(precs))}\% and {int(max(precs)) + 1}\%, the highest value being that of \cnoj{{}}")
C("No-Judge has the highest precision of all", float(NJ["prec"]) == max(precs + [float(F["prec"])]))

# ── per project ───────────────────────────────────────────────────────────
PROJ = ("Chart", "Closure", "Lang", "Math", "Mockito", "Time")
proj, nproj = {}, {}
sec5 = rep.split("## 5.")[1].split("\n## ")[0]
for p in PROJ:
    g = R(rf"\| {p} \| (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+) \|", sec5)
    nproj[p] = int(g[0])
    proj[p] = [(int(g[i]), int(g[i + 1])) for i in range(1, 7, 2)]       # (plausible, correct) per arm
for i, arm in enumerate(ARMS):
    T(f"per-project table, {arm}", MACRO[arm] + " & " + " & ".join(f"{proj[p][i][0]}/{proj[p][i][1]}" for p in PROJ) + r" \\")
T("per-project table, bugs", " & ".join(str(nproj[p]) for p in PROJ) + r" \\" + "\n" + r"\midrule" + "\n" + MACRO["full"])
T("benchmark: bugs per project", "leaving " + str(N_BUGS) + " active bugs: " + ", ".join(f"{p} {nproj[p]}" for p in PROJ) + ".")
C("bugs per project add up", sum(nproj.values()) == N_BUGS)
T("per project: range of bugs", rf"with {min(nproj.values())} to {max(nproj.values())} bugs per project")
T("results table, bugs", r"\quad bugs & " + " & ".join(str(nproj[p]) for p in PROJ) + f" & {N_BUGS} & " + r"\\")
base = re.search(r"\nTBar .*?\n\\midrule", tex, re.S).group(0)
best = [0] * 6
for line in base.strip().split("\n")[:-1]:
    cells = [c.strip() for c in line.rstrip("\\ ").split("&")]
    for k_ in range(6):
        best[k_] = max(best[k_], int(cells[1 + k_].split("/")[0]))
res = " & ".join((r"\textbf{%d}/%d" if proj[p][0][1] > best[k_] else "%d/%d") % (proj[p][0][1], proj[p][0][0]) for k_, p in enumerate(PROJ))
T("results table, SV-ARP row (bold where it has the most correct fixes)", r"\quad correct/plausible & " + res + f" & {F['co']}/{F['pl']} & ")
more = [p for k_, p in enumerate(PROJ) if 44 >= 0 and int(re.search(r"VibeRepair \(GPT-4o\)\s+&(.*?)\\\\", tex).group(1).split("&")[k_].split("/")[0]) > proj[p][0][1]]
C("VibeRepair has more correct fixes on Chart, Closure and Lang and fewer on the others", more == ["Chart", "Closure", "Lang"])
co = {p: [proj[p][i][1] for i in range(3)] for p in PROJ}
for where in ("RQ3", "appendix D"):
    pass
T("per project: Time and Chart (appendix)", rf"On Time the \cnoj{{}} configuration obtains the most correct fixes ({co['Time'][2]} against {co['Time'][0]} for \cfull{{}}), and the three configurations are level on Chart ({co['Chart'][0]}); \cfull{{}} has the most on Closure, Math and Mockito and shares the most on Lang with \cnoj{{}} ({co['Lang'][0]})")
T("per project: Full and No-Judge", r"the differences between \cfull{} and \cnoj{} are within run-to-run variation")
C("the three configurations are level on Chart", co["Chart"][0] == co["Chart"][1] == co["Chart"][2])
C("No-Judge alone has the most on Time", co["Time"][2] > max(co["Time"][:2]))
C("Full and No-Judge share the most on Lang", co["Lang"][0] == co["Lang"][2] == max(co["Lang"]) and co["Lang"][1] < co["Lang"][0])
C("Full alone has the most on Closure, Math and Mockito", all(co[p][0] > max(co[p][1:]) for p in ("Closure", "Math", "Mockito")))
C("Binary-Only has the fewest on every project, alone or tied", all(co[p][1] == min(co[p]) for p in PROJ))
share = sorted(100 * proj[p][0][1] / nproj[p] for p in PROJ if p != "Closure")
T("Closure hardest", rf"({proj['Closure'][0][1]} of {nproj['Closure']}, {pct(proj['Closure'][0][1], nproj['Closure'])}\%, against {int(share[0])}\% to {int(share[-1])}\% for the others)")
mf = R(r"full arm, multi-file bugs: (\d+), plausible (\d+), correct (\d+) \(([\d.]+)%\); single-file bugs: (\d+), correct (\d+) \(([\d.]+)%\)")
T("multi-file", rf"Of the {N_BUGS} bugs, {mf[0]} require edits to more than one source file. \svarp{{}} repairs {mf[2]} of them ({mf[3]}\%), all verified correct, against {mf[5]} of {mf[4]} single-file bugs ({mf[6]}\%)")
C("every plausible multi-file patch is correct", mf[1] == mf[2])
T("multi-file bugs and the mechanisms", rf"The {mf[0]} multi-file bugs take no part in them")
T("offline review: multi-file patches", rf"For the {WORDS[int(mf[1])]} multi-file patches the reviewers saw the first modified file only")
fa = R(r"full arm, share of each project's plausible patches found at the first attempt: Chart \d+/\d+ = ([\d.]+)%, Closure \d+/\d+ = ([\d.]+)%, Lang \d+/\d+ = ([\d.]+)%, Math \d+/\d+ = ([\d.]+)%, Mockito (\d+)/(\d+) = ([\d.]+)%, Time \d+/\d+ = ([\d.]+)%")
T("first-attempt share per project", rf"is {fa[7]}\% for Time, {fa[3]}\% for Math, {fa[0]}\% for Chart, {fa[2]}\% for Lang, {fa[1]}\% for Closure and {fa[6]}\% for Mockito ({fa[4]} of {fa[5]})")

# ── ablation table and tests ──────────────────────────────────────────────
T("ablation table, Full", rf"\cfull{{}} & {F['pl']} & {F['acc']} & {F['co']} & {F['prec']}\% & {F['ov']} & & & & & & & {F['dc']} \\")
for arm in ARMS[1:]:
    a, s_ = arms[arm], st[arm]
    T(f"ablation table, {arm}", rf"{MACRO[arm]} & {a['pl']} & {a['acc']} & {a['co']} & {a['prec']}\% & {a['ov']} & {s_['x']}/{s_['y']} & {mp(s_['x'], s_['y'], 3)} & {fmt(exact_p(s_['x'], s_['y']) / 2, 3)} & {fmt(hs[arm], 3)} & {s_['xp']}/{s_['yp']} & {mp(s_['xp'], s_['yp'], 3)} & {a['dc']} \\")
T("pairwise: Binary-Only", rf"lowers the count of verified-correct fixes from {F['co']} to {BO['co']} and the plausible count from {F['pl']} to {BO['pl']} (Table~\ref{{tab:ablation}}); after Holm adjustment over the two tests the value is ${fmt(hs['binary_only'], 3)}$, so this difference is significant")
C("the adjusted Binary-Only value is below 0.05", hs["binary_only"] < Fraction(5, 100))
T("pairwise: No-Judge", rf"changes the count from {F['co']} to {NJ['co']} and the plausible count from {F['pl']} to {NJ['pl']}; this difference is not significant, one-sided or two-sided, before or after adjustment.")
C("the patch texts labelled on records not in the package apply to a record each", R(r"patch texts labelled on records that are not in the data \(--text-labels\): (\d+); records that take such a label: (\d+)") == ("3", "4") and "rows that match no record" not in rep)
C("No-Judge: not significant, one-sided or after adjustment", exact_p(j["x"], j["y"]) / 2 > Fraction(5, 100) and hs["no_judge"] > Fraction(5, 100))
T("surgical mode: up to ten suggestions", r"lists the suggestions the Judge has made so far, up to ten, and sets the temperature to $0.85$.")
C("surgical mode: the code lists at most ten", "unique_suggestions[:10]" in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "agentic_apr.py"), encoding="utf-8").read())
pw = dict(((a, b_), (int(x), int(y))) for a, b_, x, y in re.findall(r"- (\w+) vs (\w+): \w+-only=(\d+), \w+-only=(\d+), p=", rep))
bonj = pw[("binary_only", "no_judge")]
T("pairwise among reduced configurations", rf"Between the two reduced configurations, \cbin{{}} has {NJ['co'] - BO['co']} correct fixes fewer than \cnoj{{}} ({bonj[0]} against {bonj[1]} discordant bugs, \pval{{{mp(*bonj, 3)}}})")
C("... the discordant pairs give the difference", bonj[1] - bonj[0] == NJ["co"] - BO["co"])
q = R(r"Cochran's Q across the three arms \(correct\): Q=([\d.]+), df=2, p=([\d.]+)")
T("Cochran", rf"Cochran's $Q$ rejects the joint null over the three configurations ($Q={q[0]}$, $\mathrm{{df}}=2$, \pval{{{fmt(q[1], 3)}}})")
C("Cochran's Q rejects at 0.05", float(q[1]) < 0.05)
T("delivered-patch metric", r"equals the primary count in all three configurations")
C("delivered counts equal the primary ones", F["dc"] == F["co"] and BO["dc"] == BO["co"] and NJ["dc"] == NJ["co"])
T("reading the result", rf"{d_nj} correct fixes separate the two, fewer than separate identical first attempts")
T("reading the result: two configurations", rf"end {F['co'] - NJ['co']} fixes apart ({NJ['co']} and {F['co']}), with or without a Judge")
k = R(r"Bugs fixed by k of 3 arms: k=0: (\d+), k=1: (\d+), k=2: (\d+), k=3: (\d+) → outcome depends on the arm for (\d+) bugs")
T("k of 3", rf"for {k[4]} of {N_BUGS} bugs: {k[3]} bugs are fixed by all three configurations, {k[0]} by none, {k[1]} by exactly one and {k[2]} by two")
T("cost: difference of fixes", rf"at a difference of {d_nj} correct fixes")

# ── iterations ────────────────────────────────────────────────────────────
for a, pl, sh, cum, co_, prec in it:
    T(f"iteration table row {a}", rf"{a} & {pl} & {sh}\% & {cum}\% & {co_} & {prec}\% \\")
T("iteration table total", rf"All & {F['pl']} & & & {F['co']} & {F['prec']}\% \\")
T("RQ2 first sentence", rf"({it[0][1]} of {F['pl']}) are obtained at the first attempt, before any feedback exists; {it[1][3]}\% within two iterations and {it[2][3]}\% within three")
C("'Seventy-three percent'", first_share == "73" and "Seventy-three percent of plausible patches" in tex)
later = R(r"full arm, found after the first attempt: plausible (\d+) \(([\d.]+)%\), correct (\d+) \(([\d.]+)%\)")
C("'Fifty-four' plausible patches after the first attempt", later[0] == "54")
T("share obtained after the first attempt", rf"Fifty-four of the {F['pl']} plausible patches ({later[1]}\%) and {later[2]} of the {F['co']} correct ones ({later[3]}\%) were therefore obtained after the first attempt")
T("precision by iteration", rf"({it[0][5]}\%, {it[1][5]}\%, {it[2][5]}\% and {it[3][5]}\% over {it[0][1]}, {it[1][1]}, {it[2][1]} and {it[3][1]} patches)")
mi = R(r"mean iterations, full arm, all evaluable bugs: ([\d.]+)")
T("fourth iteration, mean iterations", rf"the fourth iteration still adds {it[3][1]} plausible and {it[3][4]} correct patches, {it[3][2]}\% of the total, and the mean number of iterations over all bugs is {mi[0]} because")
npl = R(r"full arm, bugs without a plausible patch: (\d+); iterations used: \{([^}]*)\}; stagnation aborts: ([^\n]*)")
used = dict((int(a), int(b_)) for a, b_ in re.findall(r"(\d+): (\d+)", npl[1]))
T("bugs without a plausible patch", rf"Of the {npl[0]} bugs without a plausible patch, {used[4]} used all four iterations and {sum(v for k_, v in used.items() if k_ < 4)} were ended earlier by the multi-file stagnation guard, which fired in {len(re.findall(r'after \d+ iterations', npl[2]))} \cfull{{}} runs in total, none with a plausible candidate")
C("no stagnation abort with a plausible candidate", "plausible=True" not in npl[2])
jd = {}
for arm in ("full", "binary_only"):
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\n")
    jd[arm] = dict(inv=int(g[0]), parsed=int(g[1]), unp=int(g[2]), emp=int(g[3]), skip=int(g[4]))
tk = {}
for arm in ("full", "binary_only"):
    g = R(rf"\| {arm} \| \d+ \| ([\d,]+) \| ([\d,]+) \| \d+ \| ([\d,]+) \| ([\d,]+) \| ([\d.]+)% \|")
    tk[arm] = dict(rp=int(g[0].replace(",", "")), ro=int(g[1].replace(",", "")), jp=int(g[2].replace(",", "")), jo=int(g[3].replace(",", "")), share=g[4])
calls_full = CF["calls"] + jd["full"]["inv"]
T("RQ2 answer", rf"Seventy-three percent of plausible patches are found at the first attempt and {pct(sum(int(r_[1]) for r_ in it[:3]), F['pl'], 0)}\% within three; the fourth iteration adds about {pct(it[3][1], F['pl'], 0)}\%. A bug costs an estimated \${CF['mean']} at the provider's list prices and four minutes on average, at a little over two LLM calls per tested candidate ({th(calls_full)} calls for {th(CF['cand'])} candidates); the Judge accounts for {pct(tk['full']['jp'] + tk['full']['jo'], CF['tok'], 0)}\% of the tokens and {fmt(lp18['full']['jshare'], 0)}\% of the cost")
C("'four minutes' per bug", fmt(Fraction(int(CF["s"]), 60), 0) == "4")

# ── first attempts ────────────────────────────────────────────────────────
fa1 = {}
for arm in ARMS:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \(([\d.]+)%\) \|")
    fa1[arm] = g
    T(f"replication table, {arm}", rf"{MACRO[arm]} & {g[0]} & {g[1]} & {g[2]} & {g[3]} & {g[4]} & {g[5]} ({g[6]}\%) \\")
prox = R(r"first-plausible-wins plausible=(\d+), correct=(\d+)")
T("replication table, combined", rf"Three first attempts, first plausible wins: {prox[0]} plausible, {prox[1]} correct")
p1 = [int(fa1[a][0]) for a in ARMS]
c1 = [int(fa1[a][1]) for a in ARMS]
T("first attempts: counts and spread", rf"Table~\ref{{tab:replication}} reports them, with a spread of {max(p1) - min(p1)} plausible and {max(c1) - min(c1)} correct fixes")
disc = [float(x) for x in re.findall(r"correct \d+/\d+ \(([\d.]+)% of bugs\)", rep)]
assert len(disc) == 3
for where in ("Between any two configurations, ",):
    T("first-attempt discordance range: " + where, rf"{where}{min(disc):.1f}\% to {max(disc):.1f}\% of bugs")
T("first attempts as the yardstick", rf"the {d_nj}-fix difference between \cfull{{}} and \cnoj{{}} sits inside an {max(c1) - min(c1)}-fix spread between identical first attempts")
T("first attempts: deficit of Binary-Only", rf"{c1[0] - c1[1]} of its {d_bo} fixes were lost at the first attempt ({c1[1]} against {c1[0]})")
T("after a failed first attempt: rates", rf"The other {d_bo - (c1[0] - c1[1])} fixes of that deficit arise where the configurations do differ. Of the bugs whose first attempt produced no plausible candidate, a later attempt found one for {fa1['full'][6]}\% and {fa1['no_judge'][6]}\% in \cfull{{}} and \cnoj{{}}, and for {fa1['binary_only'][6]}\% in \cbin{{}}")
lt = {}
for a1, a2, nb, pa, pb, px, py, ca, cb, cx, cy in re.findall(r"\| (\w+) vs (\w+) \| (\d+) \| (\d+) / (\d+) \| (\d+)/(\d+), p=[\d.]+ \| (\d+) / (\d+) \| (\d+)/(\d+), p=[\d.]+ \|", rep.split("## 4b.")[1].split("\n## ")[0]):
    lt[(a1, a2)] = tuple(int(v) for v in (nb, pa, pb, px, py, ca, cb, cx, cy))
    v = lt[(a1, a2)]
    T(f"later-attempts table, {a1} vs {a2}", rf"{MACRO[a1]} vs.\ {MACRO[a2]} & {v[0]} & {v[1]}/{v[2]} & {v[3]}/{v[4]} & {pt(v[3], v[4])} & {v[5]}/{v[6]} & {v[7]}/{v[8]} & {pt(v[7], v[8])} \\")
assert len(lt) == 3
fb, bj, fj = lt[("full", "binary_only")], lt[("binary_only", "no_judge")], lt[("full", "no_judge")]
C("later attempts, Full against Binary-Only: p below 0.001", exact_p(fb[7], fb[8]) < Fraction(1, 1000))
T("later attempts: Full against Binary-Only", rf"There, attempts 2 to 4 yield {fb[5]} correct fixes with the full feedback and {fb[6]} without the test output")
T("later attempts: Binary-Only against No-Judge", rf"\cbin{{}} also trails \cnoj{{}}, which has the test output and no review ({bj[5]} against {bj[6]})")
T("later attempts: Full against No-Judge", rf"while \cfull{{}} and \cnoj{{}} stay close ({fj[5]} against {fj[6]}).")
C("later attempts: Full and No-Judge do not differ significantly, Binary-Only trails both", exact_p(fj[7], fj[8]) > Fraction(5, 100) and exact_p(fb[7], fb[8]) < Fraction(5, 100) and exact_p(bj[7], bj[8]) < Fraction(5, 100))
T("RQ3 answer", rf"costs {d_bo} verified-correct fixes, and this is the one difference that survives adjustment for multiple comparisons (adjusted $p={fmt(hs['binary_only'], 3)}$); {c1[0] - c1[1]} of the {d_bo} arise at the first attempt, where the configurations do not yet differ, and {d_bo - (c1[0] - c1[1])} afterwards.")
T("RQ3 answer: the review", rf"Removing the Judge moves the count by {d_nj}, against a spread of {max(c1) - min(c1)} between three identical first attempts, and the 95\% confidence interval of that difference runs from")

# ── cost ──────────────────────────────────────────────────────────────────
def mtok(n_, nd=1):
    return fmt(Fraction(n_, 10 ** 6), nd)


for arm in ARMS:
    c = cost[arm]
    jcalls, jusd = (th(jd[arm]["inv"]), c["judge"]) if arm in jd else ("0", "0")
    C(f"Judge cost of {arm}", (float(c["judge"]) > 0) == (arm in jd))
    T(f"cost table, {arm}", rf"{MACRO[arm]} & {th(c['cand'])} & {th(c['calls'])} & {jcalls} & {mtok(lp18[arm]['tin'])} & {mtok(lp18[arm]['tout'], 2)} & {c['usd']} & {jusd} & {c['mean']} & {c['pl']} & {c['fix']} & {c['s']} \\")
kco4 = int(re.search(r"\| 4 \| sample_t010[^|]*\| \d+ \| (\d+) \| 0 \|", rep).group(1))
cc = R(r"control cost over the 4 samples: (\d+) tested candidates, (\d+) repair calls, ([\d,]+) tokens, \$([\d.]+) \(\$([\d.]+) per bug, \$([\d.]+) per correct fix\), ([\d.]+) h, (\d+) s per bug")
ce = R(r"control stopping each bug at its first plausible sample: (\d+) tested candidates, (\d+) repair calls, ([\d,]+) tokens, \$([\d.]+) \(\$([\d.]+) per bug, \$([\d.]+) per correct fix\), ([\d.]+) h, (\d+) s per bug")
kpl4 = int(re.search(r"\| 4 \| sample_t010[^|]*\| (\d+) \| \d+ \| 0 \|", rep).group(1))
for name, key, g in ((r"\cctrl{}", "control, as run", cc), (r"\quad early stop", "control, early stop", ce)):
    c18 = lp18[key]
    C(f"flat-rate estimate of the control, as logged ({key})", fmt(Fraction(int(g[2].replace(",", "")) * 35, 10 ** 8)) == g[3] == c18["flat"])
    C(f"input and output tokens of the control add up ({key})", c18["tin"] + c18["tout"] == int(g[2].replace(",", "")))
    T(f"cost table, {key}", rf"{name} & {th(g[0])} & {th(g[1])} & 0 & {mtok(c18['tin'])} & {mtok(c18['tout'], 2)} & {fmt(c18['usd'])} & 0 & {fmt(c18['usd'] / N_BUGS, 3)} & {fmt(c18['usd'] / kpl4, 3)} & {fmt(c18['usd'] / kco4, 3)} & {g[7]} \\")
CR, CE = lp18["control, as run"], lp18["control, early stop"]
ctok, etok = int(cc[2].replace(",", "")) / 1e6, int(ce[2].replace(",", "")) / 1e6
regen = R(r"\| full \| \d+ \| \d+ \| \d+ \| \d+ \| (\d+) \(([\d.]+)%\) \| (\d+) of (\d+) ")
T("cost paragraph: calls", rf"Of the {th(CF['calls'])} Repair Agent calls of \cfull{{}}, {regen[0]} were regenerations of unusable output and the others one call per file and attempt; the Judge returned {th(jd['full']['parsed'])} usable reviews")
four = R(r"three configurations together: \$([\d.]+), ([\d.]+) machine-hours")
four18 = R(r"three configurations together: \$([\d.]+)\n")
C("the three configurations together, at list prices", fmt(sum(lp18[a]["usd"] for a in ARMS)) == four18[0])
T("cost paragraph: tokens", rf"consumed {CF['tok'] / 1e6:.1f}~M tokens ({tk['full']['rp'] / 1e6:.1f}~M prompt and {tk['full']['ro'] / 1e6:.1f}~M output tokens for repair, {tk['full']['jp'] / 1e6:.1f}~M and {tk['full']['jo'] / 1e6:.1f}~M for the Judge); the cost of a bug has a median of \${CF['med']} and a maximum of \${CF['mx']}, and the configuration took {CF['h']} machine-hours on a consumer laptop. The three configurations together cost \${fmt(four18[0], 0)} and {fmt(four[1], 0)} machine-hours, and the control a further \${fmt(CR['usd'])} and {fmt(cc[6], 0)} hours")
T("cost paragraph: the flat rate", rf"(the control costs \${fmt(CR['usd'])} at list prices and \${CR['flat']} at the flat rate)")
C("... the flat rate understates the control", float(CR["flat"]) < float(fmt(CR["usd"])))
st18 = R(r"steps with a token record \(the three configurations and the control passes\): ([\d,]+); steps whose logged total is not the sum of prompt and output tokens: (\d+)")
C("no step whose total differs from prompt plus output", st18[1] == "0")
T("cost paragraph: steps", rf"In each of the {st18[0].replace(',', '{,}')} generation and review steps that carry token counts, the total reported by the API is the sum of the prompt and output tokens")
f1 = R(r"plausible patches found at the first attempt: n=\d+, median tokens ([\d,]+), median seconds ([\d.]+), median USD ([\d.]+)")
f2 = R(r"plausible patches found after iteration: n=\d+, median tokens ([\d,]+), median seconds ([\d.]+), median USD ([\d.]+)")
m1 = R(r"plausible patches found at the first attempt: n=\d+, median USD at list prices ([\d.]+)")
m2 = R(r"plausible patches found after iteration: n=\d+, median USD at list prices ([\d.]+)")
T("median cost of a fix", rf"a median of {f1[0].replace(',', '{,}')} tokens, {f1[1]}~s and \${fmt(m1[0], 3)}; a fix that needed iteration costs a median of {f2[0].replace(',', '{,}')} tokens, {f2[1]}~s and \${fmt(m2[0], 3)}")
CJ = cost["no_judge"]
T("Judge share and savings", rf"accounts for {tk['full']['share']}\% of \cfull{{}}'s tokens and {lp18['full']['jshare']}\% of its cost: removing it lowers the cost per bug to \${CJ['mean']} and the cost per correct fix from \${CF['fix']} to \${CJ['fix']}")
C("the Judge's share of the cost follows from the tokens", fmt(100 * (tk["full"]["jp"] * PRICE_IN + tk["full"]["jo"] * PRICE_OUT) / (lp18["full"]["usd"] * 10 ** 6), 1) == lp18["full"]["jshare"])
du18 = lp18["full"]["usd"] - lp18["no_judge"]["usd"]
T("incremental cost of the Judge", rf"those {d_nj} fixes cost \${fmt(du18)}, that is \${fmt(du18 / d_nj)} per additional correct fix, about fourteen times the average cost of a fix")
C("... 'about fourteen times'", 13.5 < float(du18 / d_nj) / float(lp18["full"]["usd"] / F["co"]) < 14.5)
C("... as the report gives it", R(r"- full against no_judge: \+([\d.]+) USD for \+(\d+) correct fixes, \$([\d.]+) per additional correct fix") == (fmt(du18), str(d_nj), fmt(du18 / d_nj)))
C("'half the cost' (abstract)", 0.45 < float(lp18["no_judge"]["usd"] / lp18["full"]["usd"]) < 0.55)
T("contribution 3: the cost without the Judge", rf"and lowers the cost by {fmt(100 * (1 - lp18['no_judge']['usd'] / lp18['full']['usd']), 0)}\%; that the Judge's gate is nominal")
ex18 = R(r"example trajectory \((\w+), full\): ([\d,]+) input and ([\d,]+) output tokens, ([\d,]+) in all, \$([\d.]+)")
C("the example trajectory is the bug of the figure", ex18[0] == "Closure_51" and "Closure-51" in fig_source("fig:example"))
T("figure 2: cost of the bug", rf"Cost of the bug: {ex18[3].replace(',', '{,}')} tokens, \${fmt(ex18[4], 3)}.")
C("the control uses 'half the tokens' of Full", 0.45 < ctok / (CF["tok"] / 1e6) < 0.55)
lost = {a: jd[a]["unp"] + jd[a]["emp"] for a in jd}
lp = R(r"reviews lost on a passing candidate: (\d+)")
T("lost reviews", rf"in {sum(lost.values())} of the {th(sum(jd[a]['inv'] for a in jd))} Judge invocations of the two configurations with a Judge ({sum(jd[a]['unp'] for a in jd)} unparseable and {sum(jd[a]['emp'] for a in jd)} empty responses; {lost['full']} in \cfull{{}} and {lost['binary_only']} in \cbin{{}}). {WORDS[int(lp[0])].capitalize()} of the {sum(lost.values())} fell on a test-passing candidate")
_lr = [r_ for r_ in csv.DictReader(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lost_requests.csv"), encoding="utf-8"))
       if r_["agent"] == "Judge" and r_["configuration"] in jd and r_["execution_canonical"] == "yes"]
_n503 = sum(int(r_["requests_lost"]) for r_ in _lr if r_["cause"].startswith("HTTP 503"))
_iso = sum(int(r_["requests_lost"]) for r_ in _lr if r_["cause"].startswith("HTTP 503") and r_["first_logged_at"] < "2026-11-20")
C("lost reviews: every empty response is a refusal (HTTP 503) of the run log", _n503 == sum(int(r_["requests_lost"]) for r_ in _lr) == sum(jd[a]["emp"] for a in jd))
T("lost reviews: empty responses by cause", rf"each time with the provider's answer that the model was under high demand (HTTP status 503): {WORDS[_iso]} in an isolated case, and {_n503 - _iso} in the last days of the experiments")
T("lost reviews: on a passing candidate", rf"{WORDS[int(lp[0])].capitalize()} further test-passing candidates were not accepted at once because the Judge's response was lost")
# executions that lost an attempt or a review to failed requests, from the same list
_lra = [r_ for r_ in csv.DictReader(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lost_requests.csv"), encoding="utf-8"))
        if r_["execution_canonical"] == "yes"]
_att = {(r_["configuration"], r_["bug_id"]): r_["cause"] for r_ in _lra if r_["agent"] == "Repair" and "left without model output" in r_["note"]}
_att503 = {k_ for k_, c_ in _att.items() if c_.startswith("HTTP 503")}
_rev = {(r_["configuration"], r_["bug_id"]) for r_ in _lra if r_["agent"] == "Judge" and r_["cause"].startswith("HTTP 503")
        and r_["first_logged_at"] >= "2026-11-20"} - set(_att)
C("attempts without model output: the executions named", (sorted(set(_att) - _att503), sorted(_att503)) == (
    [("sample_t045a", "Closure_4")],
    sorted([("full", "Mockito_6"), ("binary_only", "Lang_20"), ("binary_only", "Lang_30"), ("binary_only", "Lang_31"),
            ("binary_only", "Lang_39"), ("no_judge", "Lang_20"), ("no_judge", "Lang_30"), ("no_judge", "Lang_39")])))
T("attempts without model output", rf"{WORDS[len(_att)].capitalize()} executions contain such an attempt: {WORDS[len(_att) - len(_att503)]} after a loss of the network connection (Closure-4 in the second control pass) and {WORDS[len(_att503)]} under the refusals")
T("threats: the refusals of the last days", rf"which cost {WORDS[len(_att503)]} executions an attempt and {WORDS[len(_rev)]} others a review")
_tle = [r_ for r_ in csv.DictReader(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "time_limit_events.csv"), encoding="utf-8"))
        if r_["limit"] == "baseline build 180 s"]
_tlc = {c_: sum(1 for r_ in _tle if r_["configuration"] == c_) for c_ in {r_["configuration"] for r_ in _tle}}
C("baseline builds over the limit: No-Judge, Binary-Only and the third control pass only, all 15 Gradle-built bugs in No-Judge",
  set(_tlc) == {"no_judge", "binary_only", "sample_t045b"} and _tlc["no_judge"] == 15
  and all(r_["bug_id"].startswith("Mockito_") for r_ in _tle))
T("baseline builds over the limit", rf"{len(_tle)} baseline builds ran over their 180~s limit (all {_tlc['no_judge']} bugs in \cnoj{{}}, {WORDS[_tlc['binary_only']]} in \cbin{{}} and {WORDS[_tlc['sample_t045b']]} in the third control pass)")

# ── the Judge as a gate ───────────────────────────────────────────────────
gate = re.findall(r"\| (full|binary_only) \| (\w+_\d+) \| (\d) \| ([^|]+) \| ([^|]*) \| ([^|]+) \| ([^|]*) \|\n", rep)
veto = [g for g in gate if g[3].startswith("verdict")]
lostp = [g for g in gate if not g[3].startswith("verdict")]
gv = R(r"genuine vetoes \(a parsed verdict other than correct on a passing candidate\): (\d+) \((\d+) labelled correct, (\d+) overfitting; (\d+) followed by an accepted patch, (\d+) not\)")
C("the Judge declined one test-passing candidate in Full: Math-63", [g[1] for g in veto if g[0] == "full"] == ["Math_63"])
T("gate: Full", rf"In the \cfull{{}} configuration the Judge declined one test-passing candidate in {F['pl']}: on Math-63")


def names(rows):
    return [g[1].replace("_", "-") for g in rows]


vb = names(g for g in veto if g[0] == "binary_only")
nv = names(g for g in veto if g[5].strip() == "no patch accepted")
C("gate: the declined candidates without an accepted patch", len(nv) == int(gv[4]) == 1)
T("gate: the other configuration with a Judge", rf"In \cbin{{}}, the other configuration with a Judge, it declined {WORDS[len(vb)]} more ({vb[0]}, {vb[1]}, {vb[2]} and {vb[3]}). Of the {WORDS[int(gv[0])]} declined candidates, {WORDS[int(gv[2])]} were overfitting and {WORDS[int(gv[1])]} correct; in {WORDS[int(gv[3])]} cases the loop later accepted a different patch, and for {nv[0]} it ended without one")
same = [g for g in lostp if g[5].strip() == "the same text accepted later"]
diff = [g for g in lostp if g[5].strip() == "a different patch accepted later"]
none = [g for g in lostp if g[5].strip() == "no patch accepted"]
C("lost reviews on a passing candidate: what followed", (sorted((g[0], g[1]) for g in same), sorted((g[0], g[1]) for g in diff), sorted((g[0], g[1]) for g in none)) == ([("binary_only", "Lang_60"), ("full", "Math_79")], [("binary_only", "Lang_14"), ("full", "Mockito_5")], [("binary_only", "Lang_31")]))
C("... the different patches accepted are correct, the unaccepted ones overfitting", all(g[6].strip().startswith("Correct") for g in diff) and all(g[4].strip() == "Overfitting" for g in none))
T("gate: lost reviews", rf"in {WORDS[len(same) + len(diff)]} cases the loop accepted the same text or another patch later, and for {names(none)[0]} in \cbin{{}}, overfitting, none")

# ── mechanisms ────────────────────────────────────────────────────────────
mech, rgn = {}, {}
for arm in ARMS:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \((\d+)%\) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|")
    rg = R(rf"\| {arm} \| \d+ \| \d+ \| \d+ \| \d+ \| (\d+) \(([\d.]+)%\) \| (\d+) of (\d+) ")
    mech[arm], rgn[arm] = [int(v) for v in g], rg
    T(f"mechanisms table, {arm}", rf"{MACRO[arm]} & {g[0]} & {g[1]} & {g[2]} ({g[3]}\%) & {g[4]} & {g[5]} & {g[6]} & {g[7]} & {rg[0]} & {rg[2]} of {rg[3]} \\")
gF = mech["full"]
single_after = gF[0] - gF[1]
tm = R(r"- `full`: attempt 1: 0\.1: \d+; attempt 2: ([^;]*); attempt 3: ([^;]*); attempt 4: ([^\n]*)")


def temps(s_):
    return {float(a): int(b_) for a, b_ in re.findall(r"([\d.]+): (\d+)", s_)}


t2, t3, t4 = temps(tm[0]), temps(tm[1]), temps(tm[2])
T("as behaved: raised after the first failure", rf"a higher temperature was requested for {sum(v for k_, v in t2.items() if k_ > 0.1)} of {sum(t2.values())} single-file bugs")
T("as behaved: attempts above 0.1", rf"{gF[2]} of the {single_after} single-file attempts made after a failure ({pct(gF[2], single_after, 0)}\%) requested more than the initial temperature; the commonest request was $0.45$ at the second and third attempts ({t2[0.45]} of {sum(t2.values())} and {t3[0.45]} of {sum(t3.values())}) and $0.85$, surgical mode, at the fourth ({t4[0.85]} of {sum(t4.values())})")
C("0.45 is the commonest level at attempts 2 and 3, 0.85 at attempt 4", t2[0.45] == max(t2.values()) and t3[0.45] == max(t3.values()) and t4[0.85] == max(t4.values()))
shares = sorted(mech[a][3] for a in ARMS)
T("appendix C: share above 0.1", rf"({shares[0]}\% to {shares[-1]}\%; three quarters of the single-file ones")
C("'two thirds', 'three quarters of the single-file ones', 'about a hundred bugs'", all(64 <= mech[a][3] <= 69 and 0.72 <= mech[a][2] / (mech[a][0] - mech[a][1]) <= 0.78 and 90 <= mech[a][7] <= 115 for a in ARMS))
rs = sorted(Fraction(100 * int(rgn[a][0]), cost[a]["calls"]) for a in ARMS)
nu = sorted(int(rgn[a][2]) for a in ARMS)
T("appendix C: regenerations", rf"which made {fmt(rs[0], 0)}\% to {fmt(rs[-1], 0)}\% of the Repair Agent calls of a configuration (Section~\ref{{sec:rq2}}), and {rgn['full'][2]} of the {rgn['full'][3]} single-file attempts of \cfull{{}} were still left without a usable edit after two regenerations, in which case the unchanged file was tested and the iteration spent ({nu[0]} to {nu[-1]} per configuration")
sz = R(r"single-file bugs: (\d+); lines in the modified file: median (\d+), quartiles \d+ / \d+; (\d+) \([\d.]+%\) have 150 lines or more, (\d+) \([\d.]+%\) have 1,000 or more")
T("file sizes", rf"has a median of {sz[1]} lines, {pct(sz[2], sz[0], 0)}\% have 150 lines or more and {pct(sz[3], sz[0], 0)}\% have 1{{,}}000 or more")
C("single-file bugs", sz[0] == mf[4])
T("file sizes: Closure", rf"its modified files are large (a median of {R(r'median lines per project \(single-file bugs\): Chart \d+, Closure (\d+)')[0]} lines)")
cmp_ = {p: R(rf"\| {p} \| \d+ \| \d+ \| (\d+)% \|")[0] for p in PROJ + ("all",)}
T("candidates that did not compile", rf"most often on Mockito ({cmp_['Mockito']}\% of its failed candidates) and Closure ({cmp_['Closure']}\%)")
C("'nearly a fifth' of failed candidates, 'about a quarter' on Closure", 17 <= int(cmp_["all"]) <= 20 and 22 <= int(cmp_["Closure"]) <= 27 and max(cmp_, key=lambda p: int(cmp_[p]) if p != "all" else -1) == "Mockito")

# ── control ───────────────────────────────────────────────────────────────
passes = re.findall(r"\| (sample_t\d+\w?) \| ([\d.]+) \| (\d+) \| (\d+) \| (\d+) \| 0 \| \{([^}]*)\} \|", rep)
assert len(passes) == 4 and all(p_[2] == str(N_BUGS) for p_ in passes)
for i, p_ in enumerate(passes, 1):
    T(f"control table, pass {i}", rf"pass {i} & {float(p_[1]):.2f} & {p_[3]} & {p_[4]} & & & & \\")
ctl = re.findall(r"\| (\d) \| sample_t010[^|]*\| (\d+) \| (\d+) \| 0 \| (\d+)/(\d+), p=[\d.]+ \| (\d+)/(\d+), p=[\d.]+ \| (\d+)/(\d+), p=[\d.]+ \| (\d+)/(\d+), p=[\d.]+ \|", rep)
assert len(ctl) == 4
for kk, pl, co_, a1, b1, a2, b2, a3, b3, a4, b4 in ctl:
    name = {"1": "first pass", "2": "first 2 passes", "3": "first 3 passes", "4": r"all 4 passes (\cctrl{})"}[kk]
    T(f"control table, first {kk} passes", rf"{name} & & {pl} & {co_} & {a1}/{b1} & {a2}/{b2} & {a3}/{b3} & {a4}/{b4} \\" + "\n" + rf"\quad $p$ & & & & {pt(a1, b1)} & {pt(a2, b2)} & {pt(a3, b3)} & {pt(a4, b4)} \\")
kpl, kco = [int(c[1]) for c in ctl], [int(c[2]) for c in ctl]
K4 = [int(v) for v in ctl[3]]
ppl, pco = [int(p_[3]) for p_ in passes], [int(p_[4]) for p_ in passes]
T("control: a single attempt", rf"A single attempt repairs {min(ppl)} to {max(ppl)} bugs ({min(pco)} to {max(pco)} correct), whatever temperature it requested")
od = R(r"first-plausible-wins correct over all 24 sample orderings: min (\d+), max (\d+), mean ([\d.]+); union \(a correct patch in at least one sample\): (\d+)")
T("control: orderings", rf"between {od[0]} and {od[1]} correct fixes (mean {od[2]}); the union over passes, which would require an oracle to pick the correct patch, gives {od[3]}")
C("the control's plausible count is the one used for its cost", kpl[3] == kpl4)
T("abstract: control", rf"four independent attempts obtain {kco[3]} correct fixes with half the full loop's tokens, not significantly fewer than the loop without the Judge")
C("abstract: 'not significantly fewer'", exact_p(K4[9], K4[10]) > Fraction(5, 100))
T("control vs No-Judge", rf"{kpl[3]} against {NJ['pl']} plausible and {kco[3]} against {NJ['co']} correct (Table~\ref{{tab:control}})")
C("control vs No-Judge: neither difference is significant", exact_p(K4[7], K4[8]) > Fraction(5, 100) and exact_p(K4[9], K4[10]) > Fraction(5, 100))
C("control: fewer tokens than No-Judge whether or not it stops early", ctok < CJ['tok'] / 1e6 and etok < CJ['tok'] / 1e6)
T("control: what iteration bought", rf"therefore bought {NJ['co'] - kco[3]} correct fixes over resampling at the same budget")
T("control vs Full", rf"the control finds {F['pl'] - kpl[3]} fewer plausible patches and {F['co'] - kco[3]} fewer correct fixes while using half the tokens, {fmt(100 * CR['usd'] / lp18['full']['usd'], 0)}\% of the cost and {th(cc[1])} LLM calls against {th(calls_full)}")
C("control: costs more than No-Judge as run and less when it stops early", float(CR['usd']) > float(CJ['usd']) > float(CE['usd']))
C("... more as run, less with early stop, and a larger share of output", CE["usd"] < lp18["no_judge"]["usd"] < CR["usd"] and Fraction(CR["tout"], CR["tin"] + CR["tout"]) > Fraction(lp18["no_judge"]["tout"], lp18["no_judge"]["tin"] + lp18["no_judge"]["tout"]))
cv = dict((a, tuple(int(v) for v in (x, y, x2, y2))) for a, x, y, x2, y2 in re.findall(r"\| (\w+) \| (\d+)/(\d+), p=[\d.]+ \| (\d+)/(\d+), p=[\d.]+ \|\n", rep))
T("control vs Binary-Only", rf"Against \cbin{{}} it has {kco[3] - BO['co']} correct fixes more ({cv['binary_only'][3]} bugs repaired only by the control, {cv['binary_only'][2]} only by \cbin{{}}; \pval{{{mp(cv['binary_only'][2], cv['binary_only'][3])}}})")
T("RQ4 answer", rf"repair {NJ['co'] - kco[3]} bugs fewer than the four-iteration loop without the Judge ({kco[3]} against {NJ['co']} correct), for \${fmt(CR['usd'])} against \${CJ['usd']}, or \${fmt(CE['usd'])} when each bug stops at its first test-passing patch, and {F['co'] - kco[3]} fewer than the full loop, which costs \${CF['usd']}")
fc = fig_source("fig:control")

# ── labels and consistency ────────────────────────────────────────────────
ident = R(r"- plausible records: (\d+); distinct patch texts: (\d+); texts recurring in two or more configurations: (\d+) \((\d+) records\)")
T("identical texts", rf"the {ident[0]} plausible records of the three configurations contain {ident[1]} distinct patch texts, {ident[2]} of which recur in two or more configurations ({ident[3]} records), and no recurring text carries two labels")
C("no recurring text carries two labels", "recurring texts whose final labels differ between configurations: none" in rep)
C("plausible records of the three configurations", int(ident[0]) == sum(a["pl"] for a in arms.values()))
ctlrec = sum(int(p_[3]) for p_ in passes)
T("patch records in all", rf"{th(int(ident[0]) + ctlrec)} patch records in all")
agr = re.findall(r"textually identical to an independently labelled arm patch for (\d+) bugs, label agreement (\d+)/(\d+); disagreements: ([^;]*); plausible patches with a recorded execution-based re-verification: (\d+)", rep)
assert len(agr) == 4
n_dis = sum(len(a[3].split("), ")) for a in agr)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ov_then = 0
for _r in csv.DictReader(open(os.path.join(_root, "data", "overrides_all.csv"), encoding="utf-8")):
    if _r["arm"].startswith("sample_t") and _r["which"] == "first" and not _r["session"].strip():
        _v = next((x for x in csv.DictReader(open(os.path.join(_root, "data", "verification", f"verification_{_r['arm']}.csv"), encoding="utf-8", errors="replace"))
                   if x["Bug_id"] == _r["bug_id"]), None)
        if _v and (_v.get("Logged plausible by the suite") or "").strip().lower() == "yes" and (_v.get("Reviewer Semantic verdict") or "").startswith(("Correct", "Overfitting")):
            _ov_then += 1
first_labelled = sum(int(re.search(r"'verification': (\d+)", p_[5]).group(1)) for p_ in passes) + _ov_then
dis_texts = sorted({x.split(" (")[0].strip() for a in agr for x in a[3].split("), ") if x.strip()}, key=lambda b_: (b_.split("_")[0], int(b_.split("_")[1])))
T("control label agreement", rf"{sum(int(a[0]) for a in agr)} of the {first_labelled} control records labelled when the control was run are textually identical to a configuration patch that was labelled independently of the control; the control labels agree with the final configuration labels on {sum(int(a[1]) for a in agr)} of them, and the {WORDS[n_dis]} disagreements are {WORDS[len(dis_texts)]} texts")
C("control label agreement: the texts named", dis_texts == ["Closure_9", "Math_90", "Math_94"])
T("control: execution-based re-verification", rf"for {sum(int(a[4]) for a in agr)} of the {first_labelled} patch records they then had, an execution-based re-verification")
k2 = R(r"Independent review 2 \(blind\): n=(\d+), agreement=([\d.]+)%, κ=([\d.]+) \[95% bootstrap CI ([\d.]+), ([\d.]+)\], disagreements=(\d+)")
k3 = R(r"Independent review 3 \(blind\): n=(\d+), agreement=([\d.]+)%, κ=([\d.]+) \[95% bootstrap CI ([\d.]+), ([\d.]+)\], disagreements=(\d+)")
T("blind passes", rf"on {int(k2[0]) - int(k2[5])} of {k2[0]} patches ($\kappa={fmt(k2[2])}$, 95\% bootstrap interval ${k2[3]}$ to ${k2[4]}$; \citealp{{cohen1960}}) and with the pass-3 labels on {int(k3[0]) - int(k3[5])} of {k3[0]} ($\kappa={fmt(k3[2])}$, ${k3[3]}$ to ${k3[4]}$)")
exc = R(r"Bugs whose blind passes reviewed the patch of another execution, excluded here: (\d+) \(([^)]*)\)")
C("patches left out of the blind-pass figures: 16, eight of them of the Mockito bugs", int(exc[0]) == 16 and sum(x.startswith("Mockito") for x in exc[1].split(", ")) == 8 and int(k3[0]) + 16 == F["pl"])
T("blind passes: the texts they read", rf"These passes read the text of {k3[0]} of the {F['pl']} plausible patches reported for \cfull{{}}.")
T("blind passes: left out of both figures", rf"the {exc[0]} patches whose text the blind passes did not read are left out of both figures")
# the others, by the source of their label (section 2b lists the records of the session executed after the verification)
sec2b = rep.split("## 2b.")[1].split("- `binary_only`")[0]
src2b = {b_: (lab_.strip(), src_.strip()) for b_, lab_, src_ in re.findall(r"\n  \| (\w+) \| [^|\n]* \| [^|\n]* \| ([^|\n]*) \| ([^|\n]*) \|", sec2b)}
not_read = [x for x in exc[1].split(", ") if not x.startswith("Mockito")]
C("blind passes: every other patch is a record of the session executed after them", all(b_ in src2b for b_ in not_read))
carried = [b_ for b_ in not_read if src2b[b_][1].startswith("identical labelled patch")]
later = [b_ for b_ in not_read if src2b[b_][1] == "labelled after the re-execution"]
ident_ = [b_ for b_ in carried if src2b[b_][0] == "Correct (identical)"]
C("blind passes: the other patches are carried over or labelled later", sorted(carried + later) == sorted(not_read) and len(ident_) == 3)
def _names(bs):
    bs = [b_.replace("_", "-") for b_ in bs]
    return ", ".join(bs[:-1]) + " and " + bs[-1] if len(bs) > 1 else bs[0]
T("blind passes: the 16 others", rf"Of the {exc[0]} others, {WORDS[int(exc[0]) - len(not_read)]} are those of the Mockito bugs executed last; {_names(ident_)}, all three token-identical to the developer fix, and {_names([b_ for b_ in carried if b_ not in ident_])} have the text of a patch labelled in another configuration or in the control; and {_names(later)} were labelled after these passes, under pass 1 and adjudication.")
T("data package: labels only", rf"labels only are recorded for the {WORDS[len(later)]} patches of \cfull{{}} labelled after the blind passes")
_p3 = rep.split("Independent review 3 (blind)")[1].split("\n")[0]
C("Closure-9 and Lang-16 are two of the six pass-3 disagreements, Math-90 and Math-36 two more", k3[5] == "6" and all(x in _p3 for x in ("Closure_9", "Lang_16", "Math_90", "Math_36")))
T("pass-3 disagreements", r"account for two of the six pass-3 disagreements above")
sv = {a: R(rf"- `{a}`: (\d+) patches logged plausible in the file[^;]*; canonical plausible patches whose text it reviewed: (\d+) of (\d+)") for a in ARMS}
svt = R(r"canonical plausible patches of the three configurations whose text the second verification reviewed: (\d+) of (\d+)")
C("second verification: the Full patches it read are as many as the blind passes read", sv["full"][1] == k3[0])
T("second verification coverage", rf"Of the {svt[1]} canonical patches reported here it read the text of {svt[0]}: {sv['full'][1]} of the {sv['full'][2]} of \cfull{{}} (the {k3[0]} that the blind passes read), {sv['binary_only'][1]} of the {sv['binary_only'][2]} of \cbin{{}} and {sv['no_judge'][1]} of the {sv['no_judge'][2]} of \cnoj")
ex9 = R(r"execution of the logged-plausible patches: \{'JDK 8 re-run of the relevant tests': (\d+), 'not re-run \(project could not be rebuilt\)': (\d+), 'token-identical to the developer fix, not re-executed': (\d+)\}")
T("second verification: Full", rf"the relevant tests were re-run for {ex9[0]} of the {sv['full'][0]} patches in its file; {ex9[2]} others are token-identical to the developer fix and were not re-executed, and {ex9[1]} Chart patches could not be rebuilt")
T("labels given last: records", rf"Of the {BO['pl'] + NJ['pl']} plausible records of \cbin{{}} and \cnoj{{}}, ")

# ── one execution per bug and configuration; recorded outcomes of identical candidates ──
sec2 = rep.split("## 2. Bugs executed more than once")[1].split("Records that are never canonical")[0]
C("threats: one valid execution of each bug in each configuration (section 2)", all(f"- `{a}`: none" in sec2 for a in ARMS))
d4 = R(r"- tested candidates in valid executions: (\d+); distinct texts: \d+; texts tested more than once: (\d+) \((\d+) candidates\)")
both = R(r"texts recorded both as passing and as failing: (\d+), of which (\d+) within valid executions \(([^)]*)\)")
mix = both[2].split(", ")
C("the texts with two outcomes in valid executions are Mockito texts", all(x.startswith("Mockito_") for x in mix) and len(mix) == int(both[1]))
T("appendix: identical candidates", rf"{th(d4[0])} candidates were tested in valid executions; {th(d4[1])} texts were tested more than once ({th(d4[2])} candidates), and the recorded outcome is the same at every occurrence for all but {WORDS[int(both[1])]} of them, Mockito candidates that fail a timing-dependent test in some executions and pass in others ({_names(mix)})")

# without the bugs with an attempt that received no model output
no_out = R(r"executions with an attempt that received no model output: (\d+)")[0]
s2c = R(r"Sensitivity: the paired comparisons on the (\d+) evaluable bugs without the bugs whose canonical execution in some configuration has such an attempt \(([^)]*)\):\n\n- full vs binary_only: correct (\d+) vs (\d+) [^\n]*\n- full vs no_judge: correct (\d+) vs (\d+) ")
n_out_bugs = len(s2c[1].split(", "))
T("attempts without model output: executions", rf"{WORDS[int(no_out)].capitalize()} executions contain such an attempt")
T("attempts without model output: bugs", rf"repeats the comparisons without the {WORDS[n_out_bugs]} bugs")
T("sensitivity 4: without these bugs", rf"without the {WORDS[n_out_bugs]} bugs that have an attempt without model output in some configuration (Section~\ref{{sec:failure-modes}}), the discordant pairs against \cfull{{}} are {s2c[2]} and {s2c[3]} for \cbin{{}} (\pval{{{mp(s2c[2], s2c[3], 3)}}}) and {s2c[4]} and {s2c[5]} for \cnoj{{}} (\pval{{{mp(s2c[4], s2c[5])}}})")
C("bugs left without them", int(s2c[0]) == N_BUGS - n_out_bugs)
# without the 15 Mockito bugs
sec = rep.split("## 14c.")[1].split("\n## ")[0]
m15 = {arm: R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+)/(\d+) \| [\d.]+ \| [\d.]+ \| (\d+)/(\d+) \| [\d.]+ \|", sec) for arm in ARMS[1:]}
m15f = R(r"\| full \| (\d+) \| (\d+) \| \| \| \| \| \|", sec)
on15 = R(r"on the 15 bugs themselves \(plausible / correct\): full (\d+) / (\d+); binary_only (\d+) / (\d+); no_judge (\d+) / (\d+)", sec)
hs3 = dict(zip(ARMS[1:], holm([exact_p(m15[a][2], m15[a][3]) for a in ARMS[1:]])))
b__, c_ = m15["binary_only"], m15["no_judge"]
T("sensitivity 5: without the 15 Mockito bugs", rf"the {N_BUGS - 15} other bugs give {m15f[1]} correct fixes for \cfull{{}} against {b__[1]} and {c_[1]} (\pval{{{mp(b__[2], b__[3], 3)}}} and \pval{{{mp(c_[2], c_[3])}}}; Holm-adjusted ${fmt(hs3['binary_only'], 3)}$ for \cbin{{}}).")
for where in ("They add ", ""):
    pass
T("threats: the 15 Mockito bugs", rf"they add {on15[0]}, {on15[2]} and {on15[4]} plausible and {on15[1]}, {on15[3]} and {on15[5]} correct fixes to the three configurations")
C("counts on the two parts add up", all(int(m15[a][1]) + int(on15[2 * i + 3]) == arms[a]["co"] for i, a in enumerate(ARMS[1:])) and int(m15f[1]) + int(on15[1]) == F["co"])
pass                                  # the coverage of the offline review is checked with the reviewers below

# ── false negatives ───────────────────────────────────────────────────────
fn = {}
for arm in ARMS:
    g = R(rf"\| {arm} \| [A-Za-z_0-9, ():]+ \| (\d+) \| (\d+) \| ([^|]*)\|\n")
    fn[arm] = (g[0], g[1], g[2].strip())
fc_ = R(r"\| control \(best of 4\) \| [A-Za-z_0-9, ]+ \| (\d+) \| (\d+) \| (\d+)/(\d+), p=([\d.]+)")


def xy(s_):
    return re.match(r"(\d+)/(\d+), p=", s_).groups()


b__, c_ = xy(fn["binary_only"][2]), xy(fn["no_judge"][2])
T("false negatives, appendix", rf"gives {fn['full'][0]}, {fn['binary_only'][0]} and {fn['no_judge'][0]} plausible and {fn['full'][1]}, {fn['binary_only'][1]} and {fn['no_judge'][1]} correct fixes for the three configurations, and {fc_[0]} and {fc_[1]} for the control. The comparisons against \cfull{{}} become {b__[0]} against {b__[1]} discordant bugs (\pval{{{mp(*b__, 3)}}}) and {c_[0]} against {c_[1]} (\pval{{{mp(*c_)}}}), and {fc_[2]} against {fc_[3]} for the control (\pval{{{mp(fc_[2], fc_[3])}}})")
T("sensitivity 3: false negatives", rf"gives {fn['full'][1]}, {fn['binary_only'][1]} and {fn['no_judge'][1]} correct fixes (\pval{{{mp(*b__, 3)}}} and \pval{{{mp(*c_)}}} against \cfull")
pre = dict((a, (int(nb), bugs)) for a, nb, bugs in re.findall(r"\| (\w+) \| (\d+) \| \d+ \| Chart 0, Closure 0, Lang 0, Math 0, Mockito \d+, Time 0 \| ([^|]*) \|", rep))
cnt = sorted(v_[0] for v_ in pre.values())
T("baseline failures outside the trigger tests", rf"the configurations have between {WORDS[cnt[0]]} and {WORDS[cnt[-1]]} such bugs, all among Mockito-22 to Mockito-26 ({WORDS[pre['full'][0]]} in \cfull{{}}: Mockito-25, never plausible, and Mockito-26, plausible; {WORDS[pre['no_judge'][0]]} in \cnoj{{}}")
C("... as listed", pre["full"][1].strip() == "Mockito_25 (+1, plausible=False), Mockito_26 (+1, plausible=True)" and all(re.fullmatch(r"Mockito_2[2-6]", x.split(" ")[0]) for v_ in pre.values() for x in v_[1].strip().split("), ")))
C("every trigger test fails at baseline in the four control passes", len(re.findall(rf"every trigger test fails at baseline for {N_BUGS}/{N_BUGS} bugs", rep)) == 4)

# ── power ─────────────────────────────────────────────────────────────────
nd = j["x"] + j["y"]
pw_ = R(r"conditional on the (\d+) discordant pairs of full vs no_judge: ([\d.]+) for a true difference of 20 correct fixes, ([\d.]+) for a difference of (\d+), the one observed")
C("power as the report gives it", pw_ == (str(nd), fmt(power(nd, 20)), fmt(power(nd, d_nj)), str(d_nj)))
T("power", rf"With {nd} discordant pairs, as in the comparison with \cnoj{{}}, the exact McNemar test at $\alpha=0.05$ has a power of about ${fmt(power(nd, 20))}$ for a true difference of 20 correct fixes and of about ${fmt(power(nd, d_nj))}$ for a difference of {d_nj}, the one observed")

# ── offline review ────────────────────────────────────────────────────────
rev = {}
for model, name in (("gemini_3_5_flash_lite_semantic", r"\model{}"), ("claude_sonnet_5_5_semantic", "Claude Sonnet 5.5")):
    g = R(rf"\| {model} \| (\d+) \| (\d+) \| (\d+)/(\d+) \| (\d+)/(\d+) \| (\d+)/(\d+) \| ([\d.-]+) \[([\d.-]+), ([\d.-]+)\] \|")
    rev[model] = g
    C(f"offline review, {model}: the vetoes are the overfitting and the correct patches vetoed", int(g[1]) == int(g[2]) + int(g[4]) == int(g[7]) and g[6] == g[2])
C("offline review: two reviewers in the report", set(re.findall(r"\| (\w+_semantic) \| \d+ \| \d+ \| \d+/\d+", rep.split("## 10.")[1].split("\n## ")[0])) == set(rev))
gm, cl = (rev[m_] for m_ in ("gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"))
C("offline review: Gemini judged every plausible patch, Claude Sonnet 5.5 those before the Mockito bugs", int(gm[0]) == F["pl"] and int(cl[0]) == int(m15f[0]))
T("offline review: who judged what", rf"\model{{}} judged all {gm[0]} plausible patches, and Claude Sonnet~5.5 the {cl[0]} that the configuration had before the 15 Gradle-built Mockito bugs were executed (Section~\ref{{sec:benchmark}})")
GEM_, SON_ = "gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"
def _vlist(model, kind):
    line = [l_ for l_ in rep.split(f"| {model} |")[1].split("\n")[1:3] if l_.strip().startswith(f"- vetoed, {kind}:")]
    assert len(line) == 1
    return [x_.split(" [")[0] for x_ in line[0].split(":", 1)[1].strip().split(", ") if x_ and x_ != "none"]
g_over, g_corr, s_over, s_corr = _vlist(GEM_, "overfitting"), _vlist(GEM_, "correct"), _vlist(SON_, "overfitting"), _vlist(SON_, "correct")
gline = rep.split(f"| {GEM_} |")[1].split("\n")[2]
g_ident = [b_ for b_ in g_corr if f"{b_} [Correct (identical)]" in gline]
C("Sonnet vetoes no token-identical patch", "[Correct (identical)]" not in rep.split("| claude_sonnet_5_5_semantic |")[1].split("\n")[2])
left, left_ok = int(cl[0]) - int(cl[1]), int(cl[5]) - int(cl[4])
T("offline review: as a filter", rf"Used as a filter on these {cl[0]} patches, its vetoes would raise precision from {pct(cl[5], cl[0])}\% to {pct(left_ok, left)}\% ({left_ok} of {left}) at the cost of {cl[4]} of their {cl[5]} correct fixes")
C("Sonnet catches 'half' of the overfitting patches, at 'about one correct fix in twenty'", 2 * int(cl[2]) == int(cl[3]) and 17 <= int(cl[5]) / int(cl[4]) <= 23)
pass                                  # caption: matched set, checked below

# ── paired differences with confidence intervals (report section 15) ─────
from math import sqrt

MC = dict(MACRO, control=r"\cctrl{}")
ci = {}
for a1, a2, metric, x, y, d, lo, hi, dp, lop, hip in re.findall(r"\| (\w+) minus (\w+) \| (correct|plausible) \| (\d+) \| (\d+) \| ([+-]\d+) \| ([+-][\d.]+) to ([+-][\d.]+) \| ([+-][\d.]+) \| ([+-][\d.]+) to ([+-][\d.]+) \|", rep):
    ci[(a1, a2, metric)] = dict(x=int(x), y=int(y), d=d, lo=lo, hi=hi, dp=dp, lop=lop, hip=hip)
    d_ = (int(x) - int(y)) / N_BUGS
    se = sqrt(int(x) + int(y) - (int(x) - int(y)) ** 2 / N_BUGS) / N_BUGS
    C(f"interval of {a1} minus {a2} ({metric}) follows from its discordant pairs",
      (f"{N_BUGS * (d_ - 1.959964 * se):+.1f}", f"{N_BUGS * (d_ + 1.959964 * se):+.1f}", f"{100 * (d_ - 1.959964 * se):+.2f}", f"{100 * (d_ + 1.959964 * se):+.2f}") == (lo, hi, lop, hip))
C("intervals: the discordant pairs are those of the tests", all((ci[("full", a, "correct")]["x"], ci[("full", a, "correct")]["y"]) == (st[a]["x"], st[a]["y"]) for a in ARMS[1:])
  and (ci[("full", "control", "correct")]["x"], ci[("full", "control", "correct")]["y"]) == (K4[5], K4[6])
  and (ci[("no_judge", "control", "correct")]["x"], ci[("no_judge", "control", "correct")]["y"]) == (K4[9], K4[10]))
for a1, a2 in (("full", "binary_only"), ("full", "no_judge"), ("full", "control"), ("no_judge", "control")):
    g = ci[(a1, a2, "correct")]
    T(f"intervals table, {a1} minus {a2}", rf"{MC[a1]} minus {MC[a2]} & ${g['d']}$ & ${g['lo']}$ to ${g['hi']}$ & ${g['dp']}$ & ${g['lop']}$ to ${g['hip']}$ \\")


def ri(s_):
    """a bound in bugs, rounded to the nearest whole bug (half away from zero)"""
    return int(Decimal(s_).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def sg(n_):
    return f"${n_:+d}$"


cb, cj, cfc, cjc = (ci[k_] for k_ in (("full", "binary_only", "correct"), ("full", "no_judge", "correct"), ("full", "control", "correct"), ("no_judge", "control", "correct")))
T("intervals in RQ3", rf"{d_bo} fixes for \cbin{{}}, with an interval from {ri(cb['lo'])} to {ri(cb['hi'])}, and {d_nj} for \cnoj{{}}, with an interval from a loss of {-ri(cj['lo'])} fixes to a gain of {ri(cj['hi'])}")
T("implications: interval of the review", rf"for a gain that this study could not distinguish from zero and whose interval reaches {ri(cj['hi'])} correct fixes")
T("RQ3 answer: interval", rf"runs from a loss of {-ri(cj['lo'])} fixes to a gain of {ri(cj['hi'])}: the experiment establishes neither")
T("contribution 3: review", rf"that removing the Judge costs {d_nj} (95\% confidence interval {sg(ri(cj['lo']))} to {sg(ri(cj['hi']))}), which cannot be distinguished")
T("contribution 3: control", rf"obtain {NJ['co'] - kco[3]} correct fixes fewer than the loop without the Judge (interval {sg(ri(cjc['lo']))} to {sg(ri(cjc['hi']))};")
T("RQ4: interval against No-Judge", rf"cannot distinguish from zero (95\% confidence interval {sg(ri(cjc['lo']))} to {sg(ri(cjc['hi']))}, Table~\ref{{tab:intervals}})")
T("RQ4: interval against Full", rf"the interval of the difference in correct fixes, {sg(ri(cfc['lo']))} to {sg(ri(cfc['hi']))}, is compatible with no advantage")
T("RQ4 answer: intervals", rf"their 95\% confidence intervals, {sg(ri(cjc['lo']))} to {sg(ri(cjc['hi']))} and {sg(ri(cfc['lo']))} to {sg(ri(cfc['hi']))} correct fixes")
C("RQ4 answer: 'a gain two to three times the one observed'", 2 <= ri(cjc['hi']) / (NJ['co'] - kco[3]) <= 3 and 2 <= ri(cfc['hi']) / (F['co'] - kco[3]) <= 3)
C("RQ4: 'one twice as large as observed'", 1.9 <= ri(cfc['hi']) / (F['co'] - kco[3]) <= 2.2)
C("the interval of the comparison with No-Judge includes zero, that of Binary-Only does not", float(cj['lo']) < 0 < float(cj['hi']) and float(cb['lo']) > 0)

# ── first attempts and the temperature requested (report section 16) ─────
sec16 = rep.split("## 16.")[1].split("\n## ")[0]
runs16 = re.findall(r"\| (\w+) \| ([\d.]+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\n", sec16)
assert len(runs16) == 7 and [r_[0] for r_ in runs16[:3]] == list(ARMS)
C("every first attempt made its usual request", all(r_[2] == r_[3] == str(N_BUGS) for r_ in runs16))
req = [r_[1] for r_ in runs16]
C("the seven runs requested 0.1 four times, 0.45 twice and 0.85 once", (req.count("0.1"), req.count("0.45"), req.count("0.85")) == (4, 2, 1))
T("the seven runs, section 4.1", r"these seven runs requested $0.1$ four times, $0.45$ twice and $0.85$ once")
C("the first attempts of the configurations are those of the replication table", [(r_[4], r_[5]) for r_ in runs16[:3]] == [(str(p1[i]), str(c1[i])) for i in range(3)])
C("the passes are those of the control table", [(r_[4], r_[5]) for r_ in runs16[3:]] == [(p_[3], p_[4]) for p_ in passes])
C("first attempts: the control passes are inside the spread of the configurations", min(p1) <= min(ppl) and max(ppl) <= max(p1) and min(c1) <= min(pco) and max(pco) <= max(c1))
C("... inside the spread of the three configurations", min(p1) <= min(ppl) and max(ppl) <= max(p1) and min(c1) <= min(pco) and max(pco) <= max(c1))
o16 = R(r"over the (\d+) runs: plausible at the first attempt (\d+) to (\d+), correct (\d+) to (\d+)")
grp = {(a, b_): (n_, c_, s_, sh, lo, hi) for a, b_, n_, c_, s_, sh, lo, hi in re.findall(r"\| ([\d.]+) and ([\d.]+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+)% \| ([\d.]+)% \| ([\d.]+)% \|", sec16)}
assert len(grp) == 5
for (a, b_), (n_, c_, s_, sh, lo, hi) in grp.items():
    rng = rf"{lo}\% to {hi}\%" if int(n_) > 1 else ""
    T(f"temperature table, {a} and {b_}", (rf"${a}$ and ${b_}$ & {n_} & {th(c_)} & {th(s_)} & {sh}\% & {rng}").rstrip() + r" \\")
    C(f"share of {a} and {b_} follows from its counts", pct(s_, c_) == sh)
al = R(r"all (\d+) pairs of runs: (\d+) of (\d+) comparisons \(([\d.]+)%\), from ([\d.]+)% to ([\d.]+)% per pair")
T("temperature table, all pairs", rf"All pairs & {al[0]} & {th(al[2])} & {th(al[1])} & {al[3]}\% & {al[4]}\% to {al[5]}\% \\")
C("all pairs: sums of the groups", int(al[0]) == sum(int(v_[0]) for v_ in grp.values()) and int(al[1]) == sum(int(v_[2]) for v_ in grp.values()) and int(al[2]) == sum(int(v_[1]) for v_ in grp.values()))
T("section 4.1: same text by request", rf"for {grp[('0.1', '0.1')][3]}\% of the bugs when both runs requested $0.1$, for {grp[('0.1', '0.85')][3]}\% when one requested $0.1$ and the other $0.85$, and for {grp[('0.45', '0.45')][3]}\% when both requested $0.45$")
C("the share does not fall as the requested temperature rises", float(grp[('0.1', '0.1')][3]) <= min(float(grp[k_][3]) for k_ in grp if k_ != ('0.1', '0.1')))

# ── kinds of correct label, and the comparisons without alternative fixes (section 17) ──
sec17 = rep.split("## 17.")[1].split("\n## ")[0]
kd = {r_[0]: [int(v_) for v_ in r_[1:]] for r_ in re.findall(r"\| (\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\n", sec17)}
assert set(kd) == set(ARMS) | {"control"}        # plausible, identical, equivalent, alternative, no kind, overfitting, identical or equivalent
C("kinds: the rows add up to the headline counts", all(kd[a][1] + kd[a][2] + kd[a][3] + kd[a][4] == arms[a]["co"] and kd[a][0] == arms[a]["pl"] for a in ARMS) and kd["control"][0] == kpl[3] and sum(kd["control"][1:5]) == kco[3])
C("kinds: the split of Full is the one given in RQ1", (kd["full"][1], kd["full"][2], kd["full"][3]) == (int(split[2]), int(split[1]), int(split[0])))
kf, kb, kj, kc = (kd[a] for a in ("full", "binary_only", "no_judge", "control"))
T("kinds per configuration", rf"Of the {F['co']} correct fixes of \cfull{{}}, {kf[1]} are identical, {kf[2]} equivalent and {kf[3]} alternative; \cbin{{}} has {kb[1]}, {kb[2]} and {kb[3]}, \cnoj{{}} {kj[1]}, {kj[2]} and {kj[3]}, and the control {kc[1]}, {kc[2]} and {kc[3]}, so {kf[3] - kb[3]} of the {d_bo} fixes by which \cbin{{}} trails are a difference in alternative fixes")
byk = R(r"full minus binary_only, by kind: identical ([+-]\d+), equivalent ([+-]\d+), alternative ([+-]\d+), all correct ([+-]\d+)", sec17)
C("... as the report gives the difference by kind", (int(byk[2]), int(byk[3])) == (kf[3] - kb[3], d_bo))
alt = kf[3] - kb[3]
T("abstract: alternative fixes", rf"with alternative fixes left out ({kf[6]} against {kb[6]}) the difference is not significant")
T("contribution 3: alternative fixes", rf"the only difference that survives multiplicity correction, and one that is no longer significant when alternative fixes are left out ({kf[6]} against {kb[6]}); that removing the Judge")
T("RQ3 answer: alternative fixes", rf"{WORDS_CAP[alt]} of the {d_bo} are a surplus of alternative fixes ({kf[3]} against {kb[3]}): when alternative fixes are not counted, the difference keeps its direction ({kf[6]} against {kb[6]}) and is not significant")
C("kinds are recorded for every configuration and for the control", all(kd[a][4] == 0 for a in kd))
ovr_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "overrides_all.csv")
sr = {r_[0]: r_[1:] for r_ in re.findall(r"\| full vs (\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|", sec17)}
assert set(sr) == {"binary_only", "no_judge", "control"}
C("strict counts are the identical and equivalent patches", int(sr["binary_only"][0]) == kf[6] and int(sr["binary_only"][1]) == kb[6] and int(sr["no_judge"][1]) == kj[6] and int(sr["control"][1]) == kc[6])
T("without alternative fixes", rf"With the identical and equivalent patches alone, \cfull{{}} has {kf[6]} against {kb[6]} for \cbin{{}} ({sr['binary_only'][2]} against {sr['binary_only'][3]} discordant bugs; \pval{{{mp(sr['binary_only'][2], sr['binary_only'][3])}}}) and {kj[6]} for \cnoj{{}} ({sr['no_judge'][2]} against {sr['no_judge'][3]}; \pval{{{mp(sr['no_judge'][2], sr['no_judge'][3])}}}), and no comparison is significant")
C("without alternative fixes: no comparison is significant", all(exact_p(sr[a][2], sr[a][3]) > Fraction(5, 100) for a in sr) and int(sr["binary_only"][2]) > int(sr["binary_only"][3]))
ls = R(r"- full vs binary_only: (\d+) bugs, (\d+) / (\d+), only first (\d+), only second (\d+), p=([\d.]+)", sec17)
C("later attempts without alternative fixes: the bugs are those of the later-attempts table", int(ls[0]) == fb[0])
T("without alternative fixes: later attempts", rf"the later attempts give {ls[1]} against {ls[2]} for \cfull{{}} and \cbin{{}} (\pval{{{mp(ls[3], ls[4])}}})")
tw = R(r"patch texts that carry two kinds of correct label \(across the configurations and the control passes\): (\d+) \(([^)]*)\)", sec17)
tw_items = [x.split(": ", 1) for x in tw[1].split("; ")]
tw_where = {b_: dict((k_, set(w_.split(", "))) for k_, w_ in re.findall(r"(identical|equivalent|alternative) in ([\w, ]+?)(?= and (?:identical|equivalent|alternative) in |$)", d_)) for b_, d_ in tw_items}
CONFS = set(ARMS)
g_ie = [b_ for b_, w_ in tw_where.items() if "identical" in w_]
g_ae = [b_ for b_, w_ in tw_where.items() if set(w_) == {"alternative", "equivalent"} and w_["alternative"] <= CONFS and w_["equivalent"] == {"control"}]
C("texts with two kinds: alternative in the configurations and equivalent in the control, nothing else", not g_ie and sorted(g_ae) == sorted(tw_where) and len(tw_where) == int(tw[0]))
_plo, _phi = fmt(min(float(sr['binary_only'][4]), float(sr['binary_only'][5]), float(sr['binary_only'][6]))), fmt(max(float(sr['binary_only'][4]), float(sr['binary_only'][5]), float(sr['binary_only'][6])))
if int(tw[0]) == 1:
    T("texts with two kinds", rf"One patch text carries two kinds, that of {_names(g_ae)}, which is alternative in the configurations and equivalent in the control; counting it either way leaves the comparison with \cbin{{}} at \pval{{{_phi}}}")
    C("... 'at' one value", _plo == _phi)
else:
    T("texts with two kinds", rf"{WORDS_CAP[int(tw[0])]} patch texts carry two kinds, those of {_names(g_ae)}, which are alternative in the configurations and equivalent in the control; counting them either way leaves the comparison with \cbin{{}} between \pval{{{_plo}}} and \pval{{{_phi}}}")
if os.path.exists(ovr_csv):
    _hm = [r_ for r_ in __import__('csv').DictReader(open(ovr_csv, encoding="utf-8")) if r_["arm"] == "full"
           and r_["note"].startswith("Kind decided by the author on 2026-11-26 for every occurrence")]
    C("kinds decided for every occurrence: three Full rows, identical, and the texts no longer carry two kinds",
      sorted(r_["bug_id"] for r_ in _hm) == ["Chart_4", "Chart_7", "Chart_8"] and all(r_["semantic_verdict"] == "Correct (identical)" for r_ in _hm)
      and not any(r_["bug_id"] in tw_where for r_ in _hm))
    T("kinds decided for every occurrence", rf"For {_names(sorted(r_['bug_id'] for r_ in _hm))}, whose patch text had been labelled equivalent in the three configurations and identical in the control, the author's decision, identical, was applied to every occurrence.")
ph = dict((a, (x, y, p_, h_)) for a, x, y, p_, h_ in re.findall(r"(\w+) (\d+)/(\d+), p=([\d.]+), Holm ([\d.]+)", sec17))
C("plausible, Holm over the two: as the report gives it", fmt(holm([exact_p(st[a]["xp"], st[a]["yp"]) for a in ARMS[1:]])[ARMS[1:].index("binary_only")], 4) == ph["binary_only"][3] and (int(ph["binary_only"][0]), int(ph["binary_only"][1])) == (b["xp"], b["yp"]))
T("plausible counts involve no label", rf"The comparison that involves no label is the plausible count (\pval{{{mp(b['xp'], b['yp'], 3)}}}, and ${fmt(ph['binary_only'][3], 3)}$ after Holm adjustment over the two comparisons), and, on the bugs whose first attempt failed in both configurations, the plausible count of the later attempts ({fb[1]} against {fb[2]}, \pval{{{mp(fb[3], fb[4], 3)}}})")
C("the plausible difference survives Holm adjustment", float(ph["binary_only"][3]) < 0.05)

# ── the reviewers as filters and on the same patches (report section 10) ──
flt = {}
for model in rev:
    flt[model] = R(rf"\| {model} \| (\d+) \| ([\d.]+)% \| (\d+)/(\d+) \| (\d+)/(\d+) \| (\d+) \| (\d+) \(([\d.]+)%\) \| ([\d.]+)% \|")
fg, fcl = (flt[m_] for m_ in ("gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"))
C("filters: the rows are those of the review table", all((flt[m_][0], flt[m_][2], flt[m_][4]) == (rev[m_][0], rev[m_][2], rev[m_][4]) for m_ in rev))
pass                                  # filters: matched set, checked below
T("offline review: what Sonnet leaves", rf"{fcl[7]} of the {fcl[6]} patches it keeps ({fcl[8]}\%) are still overfitting")
C("... consistent with the filter sentence", (int(fcl[6]), fcl[9]) == (left, pct(left_ok, left)))
blkA = rep.split("Matched set, the patches scored for every reviewer")[1].split("Matched set, the same without")[0]
blkB = rep.split("Matched set, the same without the multi-file patches")[1].split("\n## ")[0]
mA = re.match(r": (\d+) patches \((\d+) overfitting, (\d+) correct\)", blkA).groups()
mB = re.match(r": (\d+) patches \((\d+) overfitting, (\d+) correct\)", blkB).groups()
rowA = {m_: R(rf"\| {m_} \| (\d+)/(\d+) \| (\d+)/(\d+) \| ([\d.-]+) \| ([\d.]+)% \| ([\d.]+)% \|", blkA) for m_ in rev}
rowB = {m_: R(rf"\| {m_} \| (\d+)/(\d+) \| (\d+)/(\d+) \| ([\d.-]+) \| ([\d.]+)% \| ([\d.]+)% \|", blkB) for m_ in rev}
ga, ca = (rowA[m_] for m_ in (GEM_, SON_))
gb_, cb_ = (rowB[m_] for m_ in (GEM_, SON_))
T("offline review: the matched set", rf"The two reviewers are compared on these {mA[0]} patches, {mA[1]} overfitting and {mA[2]} correct")
C("the matched set is the set Claude Sonnet 5.5 judged", int(mA[0]) == int(cl[0]) and (mA[1], mA[2]) == (cl[3], cl[5]))
T("offline review: without the multi-file patches", rf"Without the {WORDS[int(mA[0]) - int(mB[0])]} multi-file patches of the set, of which the reviewers saw one file, the counts are the same.")
C("... the counts are the same", (gb_[0], cb_[0], gb_[2], cb_[2]) == (ga[0], ca[0], ga[2], ca[2]))
C("the ranking of the reviewers is the same on the matched set", float(ca[4]) > float(ga[4]) and float(cl[8]) > float(gm[8]))
C("abstract, conclusion: the interval of the in-loop reviewer includes zero", float(gm[9]) < 0 < float(gm[10]) and float(cl[9]) > 0)
# the inspection passes missed Closure-9, Lang-16 and Math-44 (Section 4.5 and Appendix A)
C("the in-loop reviewer vetoes Lang-16 and Math-90 and keeps Closure-9, Math-44 and Math-36", {"Lang_16", "Math_90"} <= set(g_over) and not {"Closure_9", "Math_44", "Math_36"} & set(g_over))
T("offline review: the in-loop reviewer and the patches the inspection missed", "Of the five patches whose overfitting the inspection passes of the verification protocol missed, it vetoes Lang-16 and Math-90,")
C("Claude Sonnet 5.5 catches Lang-16, Math-44 and Math-36 and misses Closure-9, Math-90, Time-9, Time-13 and Math-92", {"Lang_16", "Math_44", "Math_36"} <= set(s_over) and not {"Closure_9", "Math_90", "Time_9", "Time_13", "Math_92"} & set(s_over))
T("offline review: Sonnet and the patches the inspection missed", "Lang-16 and Math-44, two of the five that the inspection passes of the verification protocol missed")

# ── cost at smaller budgets and at equal spending (report section 18) ─────
sec18 = rep.split("## 18.")[1].split("\n## ")[0]
bud = {}
for name, k_, pl_, co_, tin, tout, usd_ in re.findall(r"\| ([\w, ]+?) \| (\d) \| (\d+) \| (\d+) \| ([\d,]+) \| ([\d,]+) \| \$([\d.]+) \| \$[\d.]+ \|", sec18):
    bud[(name, int(k_))] = dict(pl=int(pl_), co=int(co_), usd=usd_)
    C(f"budget table: cost of {name} at k={k_} follows from its tokens",
      fmt((int(tin.replace(",", "")) * PRICE_IN + int(tout.replace(",", "")) * PRICE_OUT) / 10 ** 6) == usd_)
assert len(bud) == 20
C("budget table: the full budget is the table of costs", all(bud[(a, 4)]["usd"] == cost[a]["usd"] and bud[(a, 4)]["co"] == arms[a]["co"] for a in ARMS)
  and bud[("control, as run", 4)]["usd"] == fmt(CR["usd"]) and bud[("control, early stop", 4)]["usd"] == fmt(CE["usd"]))
C("budget table: the control at k passes is the control table", [bud[("control, as run", k_)]["co"] for k_ in (1, 2, 3, 4)] == kco)
C("control figure: every method at each budget k", re.findall(r"coordinates \{([^}]*)\};", fc) == [" ".join(f"({i + 1},{v})" for i, v in enumerate(k)) for k in
  (kpl, kco) + tuple([bud[(a_, k_)][m_] for k_ in (1, 2, 3, 4)] for a_ in ("full", "no_judge") for m_ in ("pl", "co"))])
C("control figure: no horizontal reference lines left", "domain=1:4" not in fc)
kk18 = {(int(k_), a): (co_, u_, cc_, cu_, x, y) for k_, a, co_, u_, cc_, cu_, x, y in
        re.findall(r"\| (\d) \| (\w+) \| (\d+) \| \$([\d.]+) \| (\d+) \| \$([\d.]+) \| (\d+)/(\d+) \| [\d.]+ \|", sec18)}
assert len(kk18) == 8
nj18 = [kk18[(k_, "no_judge")] for k_ in (2, 3, 4)]
C("equal spending: the rows are those of the budget table", all(int(v[0]) == bud[("no_judge", k_)]["co"] and v[1] == bud[("no_judge", k_)]["usd"]
                                                               and int(v[2]) == kco[k_ - 1] and v[3] == bud[("control, as run", k_)]["usd"] for k_, v in zip((2, 3, 4), nj18)))
T("equal spending: the loop without the Judge against the same number of attempts",
  rf"the loop without the Judge has {nj18[0][0]}, {nj18[1][0]} and {nj18[2][0]} correct fixes, against {nj18[0][2]}, {nj18[1][2]} and {nj18[2][2]} for the same number of independent attempts, at nearly the same cost (\${nj18[0][1]}, \${nj18[1][1]} and \${nj18[2][1]} against \${nj18[0][3]}, \${nj18[1][3]} and \${nj18[2][3]}); none of the three differences is significant (\pval{{{mp(nj18[0][4], nj18[0][5])}}}, \pval{{{mp(nj18[1][4], nj18[1][5])}}} and \pval{{{mp(nj18[2][4], nj18[2][5])}}})")
C("... none is significant, and the costs are within a tenth of one another", all(exact_p(v[4], v[5]) > Fraction(5, 100) and abs(float(v[1]) / float(v[3]) - 1) < 0.1 for v in nj18))
eq = R(r"- full, k=2: \$([\d.]+), (\d+) correct; no_judge-only (\d+), other-only (\d+), p=[\d.]+", sec18)
C("equal spending: Full after two iterations is the row of the budget table", (eq[0], int(eq[1])) == (bud[("full", 2)]["usd"], bud[("full", 2)]["co"]))
T("equal spending: the full loop after two iterations", rf"the full loop completes two: {eq[1]} correct fixes for \${eq[0]}, against {NJ['co']} for \${CJ['usd']} ({eq[2]} bugs fixed only by the loop without the Judge, {eq[3]} only by the full loop; \pval{{{mp(eq[2], eq[3], 3)}}})")
C("... 'these data do not establish' the difference", exact_p(eq[2], eq[3]) > Fraction(5, 100) and abs(float(eq[0]) / float(CJ["usd"]) - 1) < 0.1)
T("discussion: cost of four independent attempts", rf"for {fmt(100 * CE['usd'] / lp18['full']['usd'], 0)}\% to {fmt(100 * CR['usd'] / lp18['full']['usd'], 0)}\% of the cost of the full loop")
T("implications: cost per correct fix without a reviewer", rf"independent attempts stopped at the first test-passing patch (\${fmt(CE['usd'] / kco[3], 3)} per correct fix) and the loop on the raw test output (\${CJ['fix']}, with {NJ['co'] - kco[3]} more correct fixes)")
T("implications: cost of the reviewer", rf"adding a reviewer to it raises the cost per bug by {fmt(100 * (lp18['full']['usd'] / lp18['no_judge']['usd'] - 1), 0)}\% for a gain")
ps18 = {nm: R(rf"- {nm}: \d+ requests, median ([\d,]+), 90th percentile ([\d,]+), maximum ([\d,]+)", sec18)
        for nm in ("Repair Agent prompt, first attempt", "Repair Agent prompt, later attempts", "Judge prompt")}
a18, b18, c18_ = (tuple(v.replace(",", "{,}") for v in ps18[nm]) for nm in ps18)
T("prompt sizes", rf"the first Repair Agent prompt of a file has a median of {a18[0]} tokens (90th percentile {a18[1]}, maximum {a18[2]}), a later one {b18[0]} ({b18[1]} and {b18[2]}) and a Judge prompt {c18_[0]} ({c18_[1]} and {c18_[2]})")

# ── the bugs on which two configurations share a failed first candidate (report section 19) ──
sec19 = rep.split("## 19.")[1].split("The same comparison on the bugs whose first candidates differ")[0]
sh = {(a1, a2): tuple(int(v) for v in vals) for a1, a2, *vals in
      re.findall(r"\| (\w+) vs (\w+) \| (\d+) \| \d+(?: \([^)]*\))? \| (\d+) \| (\d+) / (\d+) \| (\d+)/(\d+), p=[\d.]+ \| (\d+) / (\d+) \| (\d+)/(\d+), p=[\d.]+ \|", sec19)}
assert len(sh) == 3                                  # same first candidate, fails in both, plausible a/b, only a/b, correct a/b, only a/b
sb, sj = sh[("full", "binary_only")], sh[("full", "no_judge")]
T("shared first candidate: the bugs", rf"({sb[1]} bugs for \cfull{{}} and \cbin{{}}, {sj[1]} for \cfull{{}} and \cnoj{{}})")
C("... 'the later attempts differ in the same direction as on all bugs', 'too few bugs to be tested'",
  all(v[6] > v[7] and exact_p(v[8], v[9]) > Fraction(5, 100) for v in (sb, sj)) and fb[5] > fb[6] and fj[5] > fj[6]
  and BO["co"] < F["co"] and NJ["co"] < F["co"])
sec19b = rep.split("The same comparison on the bugs whose first candidates differ and both fail")[1].split("\n## ")[0]
ob = [int(v) for v in R(r"\| full vs binary_only \| (\d+) \| (\d+) / (\d+) \| \d+/\d+, p=[\d.]+ \| (\d+) / (\d+) \| \d+/\d+, p=[\d.]+ \|", sec19b)]
C("shared first candidate: the two parts make up the bugs of the later-attempts table", sb[1] + ob[0] == fb[0] and sb[2] + ob[1] == fb[1] and sb[3] + ob[2] == fb[2] and sb[6] + ob[3] == fb[5] and sb[7] + ob[4] == fb[6])

# ── three endpoints (report section 20) ───────────────────────────────────
sec20 = rep.split("## 20.")[1].split("\ncanonical per-bug tables")[0]
e20 = {a: (int(pl_), rng, int(co_), int(rec_), els, int(now_)) for a, pl_, rng, co_, rec_, els, now_ in
       re.findall(r"\| (\w+) \| (\d+) \| ([\d to]+) \| (\d+) \| (\d+) \| ([^|]*) \| (\d+) \|", sec20)}
assert set(e20) == set(ARMS) | {"control"}
C("endpoints: every configuration has every kind recorded", all(e20[a][3] == e20[a][2] and e20[a][5] == 0 for a in e20))
C("endpoints: the lower ends are the counts without the texts that carry two kinds", e20["full"][1].split(" to ")[0] == str(kf[6]) and e20["binary_only"][1].split(" to ")[0] == str(kb[6]))
C("endpoints table: the caption no longer speaks of a range", "recorded nowhere, which leaves a range" not in tex)
T("endpoints table, full", rf"\cfull{{}} & {F['pl']} & & {kf[6]} & & {F['co']} & \\")
T("endpoints table, binary_only", rf"\cbin{{}} & {BO['pl']} & {pt(b['xp'], b['yp'])} & {kb[6]} & {pt(sr['binary_only'][2], sr['binary_only'][3])} & {BO['co']} & {pt(b['x'], b['y'])} \\")
T("endpoints table, no_judge", rf"\cnoj{{}} & {NJ['pl']} & {pt(j['xp'], j['yp'])} & {kj[6]} & {pt(sr['no_judge'][2], sr['no_judge'][3])} & {NJ['co']} & {pt(j['x'], j['y'])} \\")
T("endpoints table, control", rf"\cctrl{{}} & {kpl[3]} & {pt(K4[3], K4[4])} & {kc[6]} & {pt(sr['control'][2], sr['control'][3])} & {kco[3]} & {pt(K4[5], K4[6])} \\")

# ── the reviewers: rates with intervals, and pairs on the matched set (report section 10) ──
def wilson(k_, n_, z=1.959964):
    ph = k_ / n_
    den = 1 + z * z / n_
    mid = (ph + z * z / (2 * n_)) / den
    half = z * sqrt(ph * (1 - ph) / n_ + z * z / (4 * n_ * n_)) / den
    return f"{100 * max(0.0, mid - half):.1f}", f"{100 * min(1.0, mid + half):.1f}"


blkC = rep.split("Confusion matrix of each reviewer against the labels, on the patches it was scored on")[1].split("Confusion matrix of each reviewer against the labels, on the matched set")[0]
cm = {}
for m_ in rev:
    g = R(rf"\| {m_} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+)/(\d+), ([\d.]+)% \[([\d.]+), ([\d.]+)\] \| (\d+)/(\d+), ([\d.]+)% \[([\d.]+), ([\d.]+)\] \| (\d+)/(\d+), ([\d.]+)% \[([\d.]+), ([\d.]+)\] \|", blkC)
    n_, tp, fp, fn_c, tn = (int(v) for v in g[:5])
    cm[m_] = dict(n=n_, tp=tp, fp=fp, fn=fn_c, tn=tn, sens=g[7:10], spec=g[12:15], prec=g[17:20])
    C(f"confusion matrix of {m_}: it is the review table's", (str(n_), str(tp), str(tp + fn_c), str(fp), str(fp + tn)) == (rev[m_][0], rev[m_][2], rev[m_][3], rev[m_][4], rev[m_][5]))
    C(f"confusion matrix of {m_}: rates and Wilson intervals follow from the counts",
      (pct(tp, tp + fn_c),) + wilson(tp, tp + fn_c) == cm[m_]["sens"] and (pct(tn, tn + fp),) + wilson(tn, tn + fp) == cm[m_]["spec"] and (pct(tp, tp + fp),) + wilson(tp, tp + fp) == cm[m_]["prec"])
order = ("gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic")
blkM = rep.split("Confusion matrix of each reviewer against the labels, on the matched set")[1].split("Pairs of reviewers on the matched set")[0]
cmM = {}
for m_ in order:
    g = R(rf"\| {m_} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+)/(\d+), ([\d.]+)% \[([\d.]+), ([\d.]+)\] \| (\d+)/(\d+), ([\d.]+)% \[([\d.]+), ([\d.]+)\] \| (\d+)/(\d+), ([\d.]+)% \[([\d.]+), ([\d.]+)\] \|", blkM)
    n_, tp, fp, fn_c, tn = (int(v) for v in g[:5])
    cmM[m_] = dict(n=n_, tp=tp, fp=fp, fn=fn_c, tn=tn, sens=g[7:10], spec=g[12:15], prec=g[17:20])
    C(f"matched confusion matrix of {m_}: rates and Wilson intervals follow from the counts",
      (pct(tp, tp + fn_c),) + wilson(tp, tp + fn_c) == cmM[m_]["sens"] and (pct(tn, tn + fp),) + wilson(tn, tn + fp) == cmM[m_]["spec"] and (pct(tp, tp + fp),) + wilson(tp, tp + fp) == cmM[m_]["prec"])
    C(f"matched confusion matrix of {m_}: the matched set of section 10", (str(n_), str(tp), str(fp)) == (mA[0], rowA[m_][0], rowA[m_][2]) and tp + fn_c == int(mA[1]) and fp + tn == int(mA[2]))
kM = {m_: R(rf"- {m_}: (\d+) patches, κ ([\d.-]+) \[([\d.-]+), ([\d.-]+)\]") for m_ in order}
C("matched kappa is the one of the matched table", all(kM[m_][1] == rowA[m_][4] and kM[m_][0] == mA[0] for m_ in order))
cg, cs = (cmM[m_] for m_ in order)


def b2(s_):
    """a bootstrap bound for the text: two decimals, or the report's three when two would round it to zero"""
    d_ = Decimal(s_)
    two = d_.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return s_ if abs(d_) < Decimal("0.01") and d_ != 0 else str(two)


def kap(k_):
    lo_, hi_ = b2(k_[2]), b2(k_[3])
    lo_ = ("$-" + lo_[1:] + "$") if lo_.startswith("-") else lo_
    return rf"{fmt(k_[1])} [{lo_}, {hi_}]"


T("offline review table: caption", rf"Offline LLM review of the {mA[0]} plausible patches of the \cfull{{}} configuration that both reviewers judged ({mA[1]} overfitting, {mA[2]} correct)")
T("offline review table: overfitting patches", rf"Overfitting: vetoed, kept & {cg['tp']}, {cg['fn']} & {cs['tp']}, {cs['fn']} \\")
T("offline review table: correct patches", rf"Correct: vetoed, kept & {cg['fp']}, {cg['tn']} & {cs['fp']}, {cs['tn']} \\")
for label, key in (("Sensitivity", "sens"), ("Specificity", "spec"), ("Veto precision", "prec")):
    T(f"offline review table: {label.lower()}", label + " & " + " & ".join(rf"{c_[key][0]}\% [{c_[key][1]}, {c_[key][2]}]" for c_ in (cg, cs)) + r" \\")
T("offline review table: kappa", r"$\kappa$ vs.\ labels & " + " & ".join(kap(kM[m_]) for m_ in order) + r" \\")
T("offline review: the in-loop reviewer on the matched set", rf"It vetoes {cg['tp'] + cg['fp']} of the {mA[0]} patches (Table~\ref{{tab:pilot}}), and the bootstrap interval of its Cohen's $\kappa$ against the verified labels includes zero.")
C("... the interval includes zero", float(kM[order[0]][2]) < 0 < float(kM[order[0]][3]) and float(kM[order[1]][2]) > 0)
T("offline review: sensitivity of the in-loop reviewer", rf"its sensitivity, {fmt(cg['sens'][0], 0)}\%, has an interval that reaches {fmt(cg['sens'][2], 0)}\%")
T("offline review: the in-loop reviewer as a filter", rf"As a filter it would move precision from {ga[5]}\% to {ga[6]}\%, by {fmt(Decimal(ga[6]) - Decimal(ga[5]), 1)} points, while keeping {cg['fn']} of the {mA[1]} overfitting patches and discarding {cg['fp']} correct fixes, {WORDS[len(g_ident)]} of them token-identical to the developer fix ({_names(g_ident)})")
C("... the vetoed correct patches are the same on all patches and on the matched set", int(cg["fp"]) == int(gm[4]))
T("RQ5 answer: the in-loop model", rf"For the in-loop model reviewing offline, agreement with the labels beyond chance is not established, and as a filter it would change precision by {fmt(Decimal(ga[6]) - Decimal(ga[5]), 1)} points while discarding {fg[4]} correct fixes")
C("the in-loop reviewer vetoes none of the patches outside the matched set", int(gm[1]) == cg["tp"] + cg["fp"] and int(gm[0]) - int(mA[0]) == 8)
T("offline review: the in-loop reviewer on all patches", rf"It vetoes none of the eight patches of the Mockito bugs executed last, so on all {gm[0]} patches it catches {gm[2]} of {gm[3]} overfitting patches and vetoes {gm[4]} of {gm[5]} correct ones ($\kappa={fmt(gm[8])}$).")
T("offline review: Sonnet on the matched set", rf"On the same patches it vetoes {cs['tp'] + cs['fp']} (Table~\ref{{tab:pilot}}), none of them among the")
T("offline review: contribution", rf"on the {mA[0]} patches that both judged, without the developer fix, \model{{}} and Claude Sonnet~5.5 detect {cg['tp']} and {cs['tp']} of {mA[1]} overfitting patches while wrongly vetoing {cg['fp']} and {cs['fp']} of {mA[2]} correct ones ($\kappa={fmt(kM[order[0]][1])}$ and ${fmt(kM[order[1]][1])}$")
T("offline review: abstract", rf"Of two offline LLM reviewers given no developer fix, agreement beyond chance is not established for the in-loop model (Cohen's kappa {fmt(kM[order[0]][1])}), and Claude Sonnet 5.5 catches {cs['tp']} of {mA[1]} overfitting patches (kappa {fmt(kM[order[1]][1])})")
prs = {(a1, a2): tuple(int(v) for v in vals) for a1, a2, *vals in
       re.findall(r"- (\w+) vs (\w+): overfitting vetoed (\d+)/(\d+), p=[\d.]+; correct vetoed (\d+)/(\d+), p=[\d.]+; agrees with the label (\d+)/(\d+), p=[\d.]+", rep)}
assert set(prs) == {(order[0], order[1])}
gc = prs[(order[0], order[1])]
only_g = sorted(set(g_over) - set(s_over))
C("pairs of reviewers: the in-loop reviewer catches two patches that Claude Sonnet 5.5 keeps, Math-63 and Math-90", gc[0] == 2 and only_g == ["Math_63", "Math_90"])
T("pairs of reviewers: overfitting patches", rf"It vetoes {gc[1]} overfitting patches that \model{{}} keeps, and \model{{}} {WORDS[gc[0]]} that Claude Sonnet~5.5 keeps, {_names(only_g)} (McNemar exact test, \pval{{{mp(gc[0], gc[1], 3)}}}); in the correct patches that they veto, the two do not differ significantly ({gc[2]} against {gc[3]} vetoed by one of them only; \pval{{{mp(gc[2], gc[3])}}})")
C("... as stated", exact_p(gc[2], gc[3]) > Fraction(5, 100))
n_ident = None
can_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "canonical", "canonical_full.csv")
if os.path.exists(can_csv):
    import csv as _csv2
    not_judged = R(r"\| claude_sonnet_5_5_semantic \| [^\n]*\| \d+ \(([^)]*)\) \|\n")[0].split(", ")
    n_ident = sum(1 for r_ in _csv2.DictReader(open(can_csv)) if r_["plausible"] == "True" and r_["semantic_label"] == "Correct (identical)" and r_["bug_id"] not in not_judged)
    T("offline review: Claude Sonnet 5.5 and the token-identical patches", rf"none of them among the {n_ident} patches that are token-identical to the developer fix.")
gsv = R(r"- gemini_3_5_flash_lite_semantic: (\d+) rows; ([\d,]+) input and ([\d,]+) output tokens")
gin_, gout_ = int(gsv[1].replace(",", "")), int(gsv[2].replace(",", ""))
gusd = (gin_ * PRICE_IN + gout_ * PRICE_OUT) / 10 ** 6
C("offline review cost of the in-loop model: 'about 1.2 USD'", fmt(gusd, 1) == "1.2")
T("offline review cost of the in-loop model", rf"Its review of the {gm[0]} patches cost about {fmt(gusd, 1)}~USD at the list prices of Section~\ref{{sec:rq2}} ({fmt(Fraction(gin_, 10 ** 6), 1)}~M input and {fmt(Fraction(gout_, 10 ** 6), 2)}~M output tokens).")

# ── statements that repeat a constant of the analysis or a count pinned elsewhere ─────────
T("cost table caption: prices", r"USD is the estimated API cost of the repair runs at the list prices given in the text, without the correctness assessment and local computing")
T("5.1: calls per bug", rf"in \cfull{{}} they took {fmt(Fraction(calls_full, N_BUGS), 1)} LLM calls per bug")
sev = R(r"- claude_sonnet_5_5_semantic: (\d+) rows; ([\d,]+) input and ([\d,]+) output tokens")
pin_, pout_ = int(sev[1].replace(",", "")), int(sev[2].replace(",", ""))
rev_usd = Fraction(pin_ * 2 + pout_ * 10, 10 ** 6)                    # Claude Sonnet 5.5: 2 and 10 USD per million tokens
C("offline review cost: 'about 12 USD'", round(float(rev_usd)) == 12 and int(sev[0]) == int(cl[0]))
T("offline review cost", rf"the review cost about 12~USD for the {cl[0]} patches ({fmt(Fraction(pin_, 10 ** 6), 1)}~M input and {fmt(Fraction(pout_, 10 ** 6), 2)}~M output tokens), {fmt(rev_usd / int(cl[0]), 3)}~USD per reviewed patch, against {CF['mean']}~USD per bug and {CF['pl']}~USD per plausible patch for the repair in \cfull{{}}")
sec21 = rep.split("## 21.")[1].split("\ncanonical per-bug tables")[0]
tp21 = R(r"- full vs binary_only \((\d+)/(\d+), significant after adjustment\): Holm-adjusted p reaches 0.05 after (\d+) changes placed against `full` \((\d+) if only correct labels of `full` change\); unadjusted p reaches 0.05 after (\d+) changes placed against `full` \((\d+) if only correct labels of `full` change\)", sec21)
up21 = re.findall(r"- full vs (\w+) \(\d+/\d+, not significant\): the Holm-adjusted p falls below 0.05 after (\d+) changes placed in favour of `full`", sec21)
C("label sensitivity: the discordant pairs are those of the test", (int(tp21[0]), int(tp21[1])) == (b["x"], b["y"]))
C("label sensitivity: one other comparison, with No-Judge", len(up21) == 1 and up21[0][0] == "no_judge")
kd21 = R(r"- kinds of the correct patches on the discordant bugs, full vs binary_only: full-only (\d+) \(identical \d+, equivalent \d+, alternative (\d+), no kind 0\); binary_only-only (\d+) \(identical \d+, equivalent \d+, alternative (\d+), no kind 0\)", sec21)
T("label sensitivity", rf"Of the {kd21[0]} bugs fixed only by \cfull{{}}, {kd21[1]} have an alternative fix, against {kd21[3]} of the {kd21[2]} fixed only by \cbin{{}}, and the significance of the comparison turns on few labels: {WORDS[int(tp21[2])]} label changes placed against \cfull{{}} would bring the Holm-adjusted $p$-value to $0.05$ or above, and {WORDS[int(tp21[4])]} the unadjusted one ({WORDS[int(tp21[3])]} and {WORDS[int(tp21[5])]} if only labels of \cfull{{}} change). In the other direction, the comparison with \cnoj{{}} would need {up21[0][1]} changes in favour of \cfull{{}} to become significant")
T("cost paragraph: the flat rate of the harness", r"at a flat rate of 0.35 per million tokens")
T("Judge: one file of a multi-file candidate", rf"the review of the {mf[0]} multi-file bugs is therefore partial")

# ── the limits of the prompts (read in the repository, when the checker runs inside it) ──
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
harness_py = os.path.join(root, "src", "agentic_apr.py")
if os.path.exists(harness_py):
    harness_src = open(harness_py, encoding="utf-8").read()
    lim = (re.search(r'return "".join\(diff\)\[:(\d+)\]', harness_src).group(1), re.search(r"max_chars:\s+int = (\d+)", harness_src).group(1),
           re.search(r'feedback.get\("test_output", ""\)\[:(\d+)\]', harness_src).group(1), re.search(r"test_results.output\[:(\d+)\]", harness_src).group(1))
    C("the two limits on the test output are the same", lim[2] == lim[3])
    T("limits of the prompts", rf"the failing-test source at {th(lim[1])} characters, a unified diff at {th(lim[0])}, the compile or test output at {th(lim[2])}, and the lists of failing tests and of regressions at eight entries each")
    C("... 'eight entries each'", "still_failing_targets[:8]" in harness_src and "regressions[:8]" in harness_src and "non_trigger_failing[:8]" in harness_src)
    T("limits of the Judge prompt", rf"the unified diff (its first {th(lim[0])} characters) and the structured test result (status, failing tests, and the first {th(lim[3])} characters of output)")
else:
    print("note: src/ not found next to the checker; the limits of the prompts were not checked")

# ── the abstract stays within the journal's limit ─────────────────────────
abstract = re.search(r"\\abstract\{(.*?)\}\n\n\\keywords", tex, re.S).group(1)
C("abstract: at most 250 words", len(re.sub(r"\\[a-zA-Z]+\{\}", "X", abstract).replace("~", " ").split()) <= 250)

print(f"{ok} checks passed, {bad} failed")
sys.exit(1 if bad else 0)
