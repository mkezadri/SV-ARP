#!/usr/bin/env python3
"""Check the figures of the manuscript against the regenerated report.

Values are read from the report with regular expressions. Each check then looks
in the manuscript for the sentence fragment or table row that carries the value,
written as the manuscript prints it, so that a value is found only in the place
where it is meant. Runs of spaces are ignored on both sides.

    python3 -I check_paper_numbers.py REPORT.md PAPER.tex

Not covered (taken from the run logs, the label files or the verification notes,
as Section 4.8 of the paper states): the account of the refused requests, the
build times, the time-limit events, and the counts of the records labelled
last.
"""
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


ARMS = ("full", "no_semantic", "binary_only", "no_judge")
MACRO = {"full": r"\cfull{}", "no_semantic": r"\cnosem{}", "binary_only": r"\cbin{}", "no_judge": r"\cnoj{}"}
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
WORDS_CAP = {k_: v_.capitalize() for k_, v_ in WORDS.items()}

# ── headline ──────────────────────────────────────────────────────────────
arms = {}
for arm in ARMS:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+)% \| (\d+) \|")
    arms[arm] = dict(pl=int(g[0]), acc=int(g[1]), co=int(g[2]), dc=int(g[3]), pend=int(g[4]), prec=g[5], ov=int(g[6]))
F, NS, BO, NJ = (arms[a] for a in ARMS)
C("no pending label", all(a["pend"] == 0 for a in arms.values()))
C("every bug evaluable", R(r"evaluable in all four arms \(the paired set\): \*\*(\d+)\*\*")[0] == str(N_BUGS))
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
d_ns, d_bo, d_nj = F["co"] - NS["co"], F["co"] - BO["co"], F["co"] - NJ["co"]
b, n, j = st["binary_only"], st["no_semantic"], st["no_judge"]

T("abstract: headline", rf"it produces {F['pl']} plausible patches, {first_share}\% of them at the first attempt, of which {F['co']} are verified correct ({pct(F['co'], N_BUGS)}\% of the bugs; precision {F['prec']}\%), at an estimated \${CF['mean']} per bug")
T("abstract: test evidence", rf"the correct fixes fall from {F['co']} to {BO['co']} (McNemar p~=~{mp(b['x'], b['y'], 3)}, Holm-adjusted {fmt(hs['binary_only'], 3)})")
T("abstract: Judge", rf"Removing the Judge leaves {NJ['co']} (p~=~{mp(j['x'], j['y'])}) at half the cost, and four independent single attempts")
T("introduction: test evidence", rf"it loses {d_bo} correct fixes, the one difference in the study that survives correction")
T("contribution 2", rf"{F['pl']} plausible and {F['co']} verified-correct patches (precision {F['prec']}\%) on the {N_BUGS} active \dfj{{}} v1.2 bugs, with at most four tested candidates per bug, at an estimated \${CF['mean']} per bug")
T("contribution 3", rf"four configurations paired on {N_BUGS} bugs, an equal-budget resampling control and a replication analysis of first attempts show that withholding the test output costs {d_bo} correct fixes, the only difference that survives multiplicity correction, ")
T("introduction: review", rf"the estimated contribution of the in-loop review, {d_nj} correct fixes, cannot be distinguished from run-to-run variation")
T("RQ1 sentence", rf"On the {N_BUGS} bugs, \svarp{{}} produces {F['pl']} plausible patches ({pct(F['pl'], N_BUGS)}\%), of which {F['co']} are verified correct ({pct(F['co'], N_BUGS)}\%). Its precision, the share of plausible patches that are correct, is {F['prec']}\% ({F['co']}/{F['pl']}); the {F['ov']} remaining patches are overfitting")
split = R(r"full arm label split: \{'Correct \(alternative\)': (\d+), 'Correct \(equivalent\)': (\d+), 'Correct \(identical\)': (\d+), 'Overfitting': (\d+)\}")
T("label split", rf"{split[2]} are token-identical to the developer fix, {split[1]} equivalent and {split[0]} alternative")
ovp = R(r"full arm, overfitting per project: Chart (\d+), Closure (\d+), Lang (\d+), Math (\d+), Mockito (\d+), Time (\d+)")
T("overfitting per project", rf"(Chart {ovp[0]}, Closure {ovp[1]}, Lang {ovp[2]}, Math {ovp[3]}, Mockito {ovp[4]}, Time {ovp[5]})")
T("discussion: precision of Full", rf"In the \cfull{{}} configuration {F['prec']}\% of the test-passing patches are labelled correct")
T("discussion: overfitting patches", rf"The {F['ov']} overfitting patches are concentrated")
T("RQ1 answer", rf"\svarp{{}} repairs {F['co']} of the {N_BUGS} active \dfj{{}} v1.2 bugs ({pct(F['co'], N_BUGS)}\%), with {F['prec']}\% of its test-passing patches verified correct. The counts")
T("conclusion: headline", rf"\svarp{{}} repairs {F['co']} of the {N_BUGS} active \dfj{{}} v1.2 bugs ({pct(F['co'], N_BUGS)}\%); {first_share}\% of its {F['pl']} test-passing patches are found at the first attempt and {F['prec']}\% of them are verified correct, at an estimated \${CF['mean']} per bug")
T("comparison with ReinFix", rf"\svarp{{}} obtains {F['pl']} and {F['co']} on {N_BUGS} bugs from at most four")
T("comparison with VibeRepair", rf"174 correct patches on 391 bugs from 15 candidates per bug, {WORDS[F['co'] - 174]} correct fix fewer than ours")
precs = [float(arms[a]["prec"]) for a in ARMS[1:]] + [float(R(r"control precision: ([\d.]+)%")[0])]
T("discussion: precision range", rf"the reduced configurations and the control lie between {int(min(precs))}\% and {int(max(precs)) + 1}\%, the highest value being that of \cnoj{{}}")
C("No-Judge has the highest precision of all", float(NJ["prec"]) == max(precs + [float(F["prec"])]))

# ── per project ───────────────────────────────────────────────────────────
PROJ = ("Chart", "Closure", "Lang", "Math", "Mockito", "Time")
proj, nproj = {}, {}
for p in PROJ:
    g = R(rf"\| {p} \| (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+) \|")
    nproj[p] = int(g[0])
    proj[p] = [(int(g[i]), int(g[i + 1])) for i in range(1, 9, 2)]       # (plausible, correct) per arm
for i, arm in enumerate(ARMS):
    T(f"per-project table, {arm}", MACRO[arm] + " & " + " & ".join(f"{proj[p][i][0]}/{proj[p][i][1]}" for p in PROJ) + r" \\")
    T(f"project figure, {arm}", "coordinates {" + " ".join(f"({p},{proj[p][i][1]})" for p in PROJ) + "}")
T("per-project table, bugs", " & ".join(str(nproj[p]) for p in PROJ) + r" \\" + "\n" + r"\midrule" + "\n" + MACRO["full"])
T("benchmark: bugs per project", "leaving " + str(N_BUGS) + " active bugs: " + ", ".join(f"{p} {nproj[p]}" for p in PROJ) + ".")
C("bugs per project add up", sum(nproj.values()) == N_BUGS)
T("per project: range of bugs", rf"With {min(nproj.values())} to {max(nproj.values())} bugs per project")
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
co = {p: [proj[p][i][1] for i in range(4)] for p in PROJ}
for where in ("RQ3", "appendix D"):
    pass
T("per project: Chart and Time (RQ3)", rf"\cnosem{{}} obtains the most correct fixes on Chart ({co['Chart'][1]} against {co['Chart'][0]} for \cfull{{}}) and \cnoj{{}} on Time ({co['Time'][3]} against {co['Time'][0]}), and \cnoj{{}} equals \cfull{{}} on Lang ({co['Lang'][0]})")
T("per project: Chart and Time (appendix)", rf"On Chart the \cnosem{{}} configuration obtains the most correct fixes ({co['Chart'][1]} against {co['Chart'][0]} for \cfull{{}}) and on Time the \cnoj{{}} configuration ({co['Time'][3]} against {co['Time'][0]}); \cfull{{}} has the most on Closure, Math and Mockito and shares the most on Lang with \cnoj{{}} ({co['Lang'][0]})")
C("No-Semantic alone has the most on Chart", co["Chart"][1] > max(co["Chart"][0], co["Chart"][2], co["Chart"][3]))
C("No-Judge alone has the most on Time", co["Time"][3] > max(co["Time"][:3]))
C("Full and No-Judge share the most on Lang", co["Lang"][0] == co["Lang"][3] == max(co["Lang"]) and co["Lang"][1] < co["Lang"][0])
C("Full alone has the most on Closure, Math and Mockito", all(co[p][0] > max(co[p][1:]) for p in ("Closure", "Math", "Mockito")))
C("Binary-Only has the fewest on every project, alone or tied", all(co[p][2] == min(co[p]) for p in PROJ))
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
T("ablation table, Full", rf"\cfull{{}} & {F['pl']} & {F['co']} & {F['prec']}\% & {F['ov']} & & & & & & & {F['dc']} \\")
for arm in ARMS[1:]:
    a, s_ = arms[arm], st[arm]
    T(f"ablation table, {arm}", rf"{MACRO[arm]} & {a['pl']} & {a['co']} & {a['prec']}\% & {a['ov']} & {s_['x']}/{s_['y']} & {mp(s_['x'], s_['y'], 3)} & {fmt(exact_p(s_['x'], s_['y']) / 2, 3)} & {fmt(hs[arm], 3)} & {s_['xp']}/{s_['yp']} & {mp(s_['xp'], s_['yp'], 3)} & {a['dc']} \\")
T("pairwise: Binary-Only", rf"lowers the count of verified-correct fixes from {F['co']} to {BO['co']}: {b['x']} bugs are fixed only by \cfull{{}} against {b['y']} fixed only by \cbin{{}} (two-sided \pval{{{mp(b['x'], b['y'], 3)}}}, one-sided \pval{{{fmt(exact_p(b['x'], b['y']) / 2, 3)}}}), and the plausible count falls from {F['pl']} to {BO['pl']} (\pval{{{mp(b['xp'], b['yp'], 3)}}}). After Holm adjustment over the three tests the value is ${fmt(hs['binary_only'], 3)}$, so this difference is significant")
C("the adjusted Binary-Only value is below 0.05", hs["binary_only"] < Fraction(5, 100))
T("pairwise: No-Judge", rf"changes the count from {F['co']} to {NJ['co']} ({j['x']} bugs fixed only by \cfull{{}} against {j['y']} fixed only by \cnoj{{}}; two-sided \pval{{{mp(j['x'], j['y'])}}}, one-sided \pval{{{fmt(exact_p(j['x'], j['y']) / 2)}}}) and the plausible count from {F['pl']} to {NJ['pl']} (\pval{{{mp(j['xp'], j['yp'])}}})")
T("pairwise: No-Semantic", rf"(\cnosem{{}}) also gives {NS['co']} ({n['x']} against {n['y']}; \pval{{{mp(n['x'], n['y'])}}}). Neither difference is significant, one-sided or two-sided, before or after adjustment (${fmt(hs['no_semantic'])}$ for both)")
C("No-Semantic and No-Judge have the same count and adjusted value", NS["co"] == NJ["co"] and fmt(hs["no_semantic"]) == fmt(hs["no_judge"]))
C("neither is significant one-sided", min(exact_p(n["x"], n["y"]), exact_p(j["x"], j["y"])) / 2 > Fraction(5, 100))
pw = dict(((a, b_), (int(x), int(y))) for a, b_, x, y in re.findall(r"- (\w+) vs (\w+): \w+-only=(\d+), \w+-only=(\d+), p=", rep))
nsbo, bonj, nsnj = pw[("no_semantic", "binary_only")], pw[("binary_only", "no_judge")], pw[("no_semantic", "no_judge")]
T("pairwise among reduced configurations", rf"\cnosem{{}} and \cnoj{{}} have the same count ({nsnj[0]} bugs each way), and \cbin{{}} has {NS['co'] - BO['co']} correct fixes fewer than either ({nsbo[1]} against {nsbo[0]} discordant bugs in both comparisons, \pval{{{mp(*nsbo, 3)}}})")
C("the two comparisons with Binary-Only have the same discordant pairs", nsbo == bonj[::-1] and nsnj[0] == nsnj[1] and NS["co"] == NJ["co"])
q = R(r"Cochran's Q across the four arms \(correct\): Q=([\d.]+), df=3, p=([\d.]+)")
T("Cochran", rf"($Q={q[0]}$, $\mathrm{{df}}=3$, \pval{{{fmt(q[1], 3)}}})")
T("delivered-patch metric", rf"moves \cnosem{{}} to {NS['dc']} and does not change these conclusions")
C("delivered counts equal the primary ones except for No-Semantic", F["dc"] == F["co"] and BO["dc"] == BO["co"] and NJ["dc"] == NJ["co"] and NS["dc"] == NS["co"] - 1)
keep = sorted((NJ["co"], NS["co"], F["co"]))
T("reading the result", rf"{d_nj} correct fixes separate the two, fewer than separate identical first attempts")
T("reading the result: three configurations", rf"end within {keep[-1] - keep[0]} fixes of one another ({keep[0]}, {keep[1]} and {keep[2]})")
k = R(r"Bugs fixed by k of 4 arms: k=0: (\d+), k=1: (\d+), k=2: (\d+), k=3: (\d+), k=4: (\d+) → outcome depends on the arm for (\d+) bugs")
T("k of 4", rf"for {k[5]} of {N_BUGS} bugs: {k[4]} bugs are fixed by all four configurations, {k[0]} by none, {k[1]} by exactly one, {k[2]} by two and {k[3]} by three")
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
for arm in ARMS[:3]:
    g = R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\n")
    jd[arm] = dict(inv=int(g[0]), parsed=int(g[1]), unp=int(g[2]), emp=int(g[3]), skip=int(g[4]))
tk = {}
for arm in ARMS[:3]:
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
T("replication table, combined", rf"Four first attempts, first plausible wins: {prox[0]} plausible, {prox[1]} correct")
p1 = [int(fa1[a][0]) for a in ARMS]
c1 = [int(fa1[a][1]) for a in ARMS]
T("first attempts: counts and spread", rf"They produce {p1[0]}, {p1[1]}, {p1[2]} and {p1[3]} plausible and {c1[0]}, {c1[1]}, {c1[2]} and {c1[3]} correct patches: a spread of {max(p1) - min(p1)} plausible and {max(c1) - min(c1)} correct fixes")
disc = [float(x) for x in re.findall(r"correct \d+/\d+ \(([\d.]+)% of bugs\)", rep)]
assert len(disc) == 6
for where in ("Between any two configurations, ", "identical first attempts, "):
    T("first-attempt discordance range: " + where, rf"{where}{min(disc):.1f}\% to {max(disc):.1f}\% of bugs")
T("first attempts as the yardstick", rf"the {d_nj}-fix differences between \cfull{{}} and the two configurations that keep the test evidence sit inside a {max(c1) - min(c1)}-fix spread between identical first attempts")
C("the two differences are equal", d_nj == d_ns)
T("first attempts: deficit of Binary-Only", rf"{c1[0] - c1[2]} of its {d_bo} fixes were lost at the first attempt ({c1[2]} against {c1[0]})")
T("first attempts combined", rf"gives {prox[0]} plausible and {prox[1]} correct fixes, a second estimate of what four independent attempts obtain")
T("after a failed first attempt: rates", rf"The other {d_bo - (c1[0] - c1[2])} fixes of that deficit arise where the configurations do differ. Of the bugs whose first attempt produced no plausible candidate, a later attempt found one for {fa1['full'][6]}\%, {fa1['no_semantic'][6]}\% and {fa1['no_judge'][6]}\% in \cfull{{}}, \cnosem{{}} and \cnoj{{}}, and for {fa1['binary_only'][6]}\% in \cbin{{}}")
lt = {}
for a1, a2, nb, pa, pb, px, py, ca, cb, cx, cy in re.findall(r"\| (\w+) vs (\w+) \| (\d+) \| (\d+) / (\d+) \| (\d+)/(\d+), p=[\d.]+ \| (\d+) / (\d+) \| (\d+)/(\d+), p=[\d.]+ \|", rep.split("## 4b.")[1].split("\n## ")[0]):
    lt[(a1, a2)] = tuple(int(v) for v in (nb, pa, pb, px, py, ca, cb, cx, cy))
    v = lt[(a1, a2)]
    T(f"later-attempts table, {a1} vs {a2}", rf"{MACRO[a1]} vs.\ {MACRO[a2]} & {v[0]} & {v[1]}/{v[2]} & {v[3]}/{v[4]} & {pt(v[3], v[4])} & {v[5]}/{v[6]} & {v[7]}/{v[8]} & {pt(v[7], v[8])} \\")
assert len(lt) == 6
fb, bj, fj, fn_ = lt[("full", "binary_only")], lt[("binary_only", "no_judge")], lt[("full", "no_judge")], lt[("full", "no_semantic")]
C("later attempts, Full against Binary-Only: p below 0.001", exact_p(fb[7], fb[8]) < Fraction(1, 1000))
T("later attempts: Full against Binary-Only", rf"On the {fb[0]} such bugs of \cfull{{}} and \cbin{{}}, attempts 2 to 4 yield {fb[5]} correct fixes with the full feedback and {fb[6]} without the test output ({fb[7]} bugs fixed only by \cfull{{}} against {fb[8]}; $p<0.001$)")
T("later attempts: Binary-Only against No-Judge", rf"\cbin{{}} yields {bj[5]} where \cnoj{{}} yields {bj[6]} ({bj[7]} against {bj[8]}; \pval{{{mp(bj[7], bj[8], 3)}}})")
T("later attempts: Full against No-Judge and No-Semantic", rf"the same restriction leaves {fj[5]} against {fj[6]} (\pval{{{mp(fj[7], fj[8])}}}), and between \cfull{{}} and \cnosem{{}} {fn_[5]} against {fn_[6]} (\pval{{{mp(fn_[7], fn_[8], 3)}}})")
T("RQ3 answer", rf"costs {d_bo} verified-correct fixes, and this is the one difference that survives adjustment for multiple comparisons (adjusted $p={fmt(hs['binary_only'], 3)}$); {c1[0] - c1[2]} of the {d_bo} arise at the first attempt, where the configurations do not yet differ, and {d_bo - (c1[0] - c1[2])} afterwards.")
T("RQ3 answer: the review", rf"Removing the Judge, or withholding its reasoning, moves the count by {d_nj}, against a spread of {max(c1) - min(c1)} between four identical first attempts, and the 95\% confidence interval of that difference runs from")

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
T("cost paragraph: calls", rf"tested {th(CF['cand'])} candidates. Generating them took {th(CF['calls'])} Repair Agent calls, of which {regen[0]} were regenerations of unusable output and the others one call per file and attempt; the Judge was called {th(jd['full']['inv'])} times and returned {th(jd['full']['parsed'])} usable reviews")
four = R(r"four configurations together: \$([\d.]+), ([\d.]+) machine-hours")
four18 = R(r"four configurations together: \$([\d.]+)\n")
C("the four configurations together, at list prices", fmt(sum(lp18[a]["usd"] for a in ARMS)) == four18[0])
T("cost paragraph: tokens", rf"consumed {CF['tok'] / 1e6:.1f}~M tokens ({tk['full']['rp'] / 1e6:.1f}~M prompt and {tk['full']['ro'] / 1e6:.1f}~M output tokens for repair, {tk['full']['jp'] / 1e6:.1f}~M and {tk['full']['jo'] / 1e6:.1f}~M for the Judge), which cost \${CF['usd']} for {N_BUGS} bugs, \${CF['repair']} for repair and \${CF['judge']} for the Judge: \${CF['mean']} per bug on average (median \${CF['med']}, maximum \${CF['mx']}), \${CF['pl']} per plausible patch and \${CF['fix']} per correct fix, at {CF['s']}~s per bug on a consumer laptop and {CF['h']} machine-hours for the configuration; the four configurations together cost \${fmt(four18[0], 0)} and {fmt(four[1], 0)} machine-hours, and the control a further \${fmt(CR['usd'])} and {fmt(cc[6], 0)} hours")
T("cost paragraph: the flat rate", rf"(the control costs \${fmt(CR['usd'])} at list prices and \${CR['flat']} at the flat rate)")
C("... the flat rate understates the control", float(CR["flat"]) < float(fmt(CR["usd"])))
st18 = R(r"steps with a token record \(the four configurations and the control passes\): ([\d,]+); steps whose logged total is not the sum of prompt and output tokens: (\d+)")
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
T("incremental cost of the Judge", rf"those {d_nj} fixes cost \${fmt(du18)}, that is \${fmt(du18 / d_nj)} per additional correct fix, about twelve times the average cost of a fix")
C("... 'about twelve times'", 11.5 < float(du18 / d_nj) / float(lp18["full"]["usd"] / F["co"]) < 12.5)
C("... as the report gives it", R(r"- full against no_judge: \+([\d.]+) USD for \+(\d+) correct fixes, \$([\d.]+) per additional correct fix") == (fmt(du18), str(d_nj), fmt(du18 / d_nj)))
C("'half the cost' (abstract)", 0.45 < float(lp18["no_judge"]["usd"] / lp18["full"]["usd"]) < 0.55)
T("contribution 3: the cost without the Judge", rf"and lowers the cost by {fmt(100 * (1 - lp18['no_judge']['usd'] / lp18['full']['usd']), 0)}\%; that the Judge's gate is nominal")
T("conclusion: the cost without the Judge", rf"a difference that the experiment does not establish, at {fmt(100 * lp18['no_judge']['usd'] / lp18['full']['usd'], 0)}\% of the cost")
ex18 = R(r"example trajectory \((\w+), full\): ([\d,]+) input and ([\d,]+) output tokens, ([\d,]+) in all, \$([\d.]+)")
C("the example trajectory is the bug of the figure", ex18[0] == "Closure_51" and "Closure-51" in fig_source("fig:example"))
T("figure 2: cost of the bug", rf"Cost of the bug: {ex18[3].replace(',', '{,}')} tokens, \${fmt(ex18[4], 3)}.")
C("the control uses 'half the tokens' of Full", 0.45 < ctok / (CF["tok"] / 1e6) < 0.55)
T("control design sentence", rf"the control tested {th(cc[0])} candidates with {th(cc[1])} Repair Agent calls, against {th(CF['cand'])} candidates, {th(CF['calls'])} Repair Agent calls and {th(jd['full']['inv'])} Judge calls in \cfull")
lost = {a: jd[a]["unp"] + jd[a]["emp"] for a in jd}
lp = R(r"reviews lost on a passing candidate: (\d+)")
T("lost reviews", rf"in {sum(lost.values())} of the {th(sum(jd[a]['inv'] for a in jd))} Judge invocations of the three configurations with a Judge ({sum(jd[a]['unp'] for a in jd)} unparseable and {sum(jd[a]['emp'] for a in jd)} empty responses; {lost['full']} in \cfull{{}}, {lost['no_semantic']} in \cnosem{{}} and {lost['binary_only']} in \cbin{{}}). {WORDS[int(lp[0])].capitalize()} of the {sum(lost.values())} fell on a test-passing candidate")
T("lost reviews: empty responses by cause", rf"For the {sum(jd[a]['emp'] for a in jd) - 1} others the provider answered")
T("lost reviews: on a passing candidate", rf"{WORDS[int(lp[0])].capitalize()} further test-passing candidates were not accepted at once because the Judge's response was lost")

# ── the Judge as a gate ───────────────────────────────────────────────────
gate = re.findall(r"\| (full|no_semantic|binary_only) \| (\w+_\d+) \| (\d) \| ([^|]+) \| ([^|]*) \| ([^|]+) \| ([^|]*) \|\n", rep)
veto = [g for g in gate if g[3].startswith("verdict")]
lostp = [g for g in gate if not g[3].startswith("verdict")]
gv = R(r"genuine vetoes \(a parsed verdict other than correct on a passing candidate\): (\d+) \((\d+) labelled correct, (\d+) overfitting; (\d+) followed by an accepted patch, (\d+) not\)")
C("the Judge declined one test-passing candidate in Full: Math-63", [g[1] for g in veto if g[0] == "full"] == ["Math_63"])
T("gate: Full", rf"In the \cfull{{}} configuration the Judge declined one test-passing candidate in {F['pl']}: on Math-63")


def names(rows):
    return [g[1].replace("_", "-") for g in rows]


vn, vb = names(g for g in veto if g[0] == "no_semantic"), names(g for g in veto if g[0] == "binary_only")
T("gate: reduced configurations", rf"it declined {WORDS[len(vn) + len(vb)]} more ({vn[0]}, {vn[1]} and {vn[2]} in \cnosem{{}}; {vb[0]}, {vb[1]}, {vb[2]} and {vb[3]} in \cbin{{}}). Of the {WORDS[int(gv[0])]} declined candidates, {WORDS[int(gv[2])]} were overfitting and {WORDS[int(gv[1])]} correct; in {WORDS[int(gv[3])]} cases the loop later accepted a different patch and in {WORDS[int(gv[4])]} it ended without one")
same = [g for g in lostp if g[5].strip() == "the same text accepted later"]
diff = [g for g in lostp if g[5].strip() == "a different patch accepted later"]
none = [g for g in lostp if g[5].strip() == "no patch accepted"]
C("lost reviews on a passing candidate: what followed", (sorted((g[0], g[1]) for g in same), sorted((g[0], g[1]) for g in diff), sorted((g[0], g[1]) for g in none)) == ([("binary_only", "Lang_60"), ("full", "Math_79")], [("binary_only", "Lang_14"), ("full", "Mockito_5")], [("binary_only", "Lang_31"), ("no_semantic", "Math_92")]))
C("... the different patches accepted are correct, the unaccepted ones overfitting", all(g[6].strip().startswith("Correct") for g in diff) and all(g[4].strip() == "Overfitting" for g in none))
T("gate: lost reviews", r"for Math-79 in \cfull{} and Lang-60 in \cbin{} the same text was regenerated and accepted at the next iteration; for Mockito-5 in \cfull{} and Lang-14 in \cbin{} the loop went on to accept a different patch, also correct; and for Math-92 in \cnosem{} and Lang-31 in \cbin{}, both overfitting, no patch was accepted")

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
T("appendix C: regenerations", rf"{rgn['full'][0]} of the {th(CF['calls'])} Repair Agent calls of \cfull{{}} were regenerations ({fmt(rs[0], 0)}\% to {fmt(rs[-1], 0)}\% across configurations), and {rgn['full'][2]} of its {rgn['full'][3]} single-file attempts were still left without a usable edit after two regenerations, in which case the unchanged file was tested and the iteration spent ({nu[0]} to {nu[-1]} per configuration")
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
T("control: passes", rf"In pass order, the first pass repairs {kpl[0]} bugs ({kco[0]} correct), and the second, third and fourth add {kpl[1] - kpl[0]}, {kpl[2] - kpl[1]} and {kpl[3] - kpl[2]} bugs: {kpl[1]}, {kpl[2]} and {kpl[3]} plausible after two, three and four passes, with {kco[1]}, {kco[2]} and {kco[3]} correct")
od = R(r"first-plausible-wins correct over all 24 sample orderings: min (\d+), max (\d+), mean ([\d.]+); union \(a correct patch in at least one sample\): (\d+)")
T("control: orderings", rf"between {od[0]} and {od[1]} correct fixes (mean {od[2]}); the union over passes, which would require an oracle to pick the correct patch, gives {od[3]}")
T("control: two estimates", rf"the first attempts of the configurations ({prox[0]} plausible, {prox[1]} correct) and the control ({kpl[3]}, {kco[3]}), are close")
C("the control's plausible count is the one used for its cost", kpl[3] == kpl4)
T("abstract: control", rf"four independent single attempts obtain {kco[3]} correct fixes with half the full loop's tokens, not significantly fewer than the loop without the Judge")
C("abstract: 'not significantly fewer'", exact_p(K4[9], K4[10]) > Fraction(5, 100))
T("control vs No-Judge", rf"{kpl[3]} against {NJ['pl']} plausible ({K4[7]} bugs repaired only by \cnoj{{}}, {K4[8]} only by the control; \pval{{{mp(K4[7], K4[8])}}}) and {kco[3]} against {NJ['co']} correct ({K4[9]} against {K4[10]}; \pval{{{mp(K4[9], K4[10])}}})")
T("control: tokens", rf"{ctok:.1f}~M as run, and {etok:.1f}~M with {th(ce[0])} tested candidates when each bug stops at its first plausible pass, against {CJ['tok'] / 1e6:.1f}~M and {th(CJ['cand'])} candidates for \cnoj")
T("control: what iteration bought", rf"therefore bought {NJ['co'] - kco[3]} correct fixes over resampling at the same budget")
T("control vs Full", rf"the control finds {F['pl'] - kpl[3]} fewer plausible patches ({K4[3]} bugs repaired only by \cfull{{}}, {K4[4]} only by the control; \pval{{{mp(K4[3], K4[4], 3)}}}) and {F['co'] - kco[3]} fewer correct fixes ({K4[5]} against {K4[6]}; \pval{{{mp(K4[5], K4[6], 3)}}}) while using half the tokens ({ctok:.1f}~M against {CF['tok'] / 1e6:.1f}~M), {fmt(100 * CR['usd'] / lp18['full']['usd'], 0)}\% of the cost (\${fmt(CR['usd'])} against \${CF['usd']}) and {th(cc[1])} LLM calls against {th(calls_full)}")
T("control: cost against No-Judge", rf"At list prices the control as run costs more than \cnoj{{}}, \${fmt(CR['usd'])} against \${CJ['usd']}, because a larger share of its tokens are output tokens, and less when it stops early (\${fmt(CE['usd'])};")
C("... more as run, less with early stop, and a larger share of output", CE["usd"] < lp18["no_judge"]["usd"] < CR["usd"] and Fraction(CR["tout"], CR["tin"] + CR["tout"]) > Fraction(lp18["no_judge"]["tout"], lp18["no_judge"]["tin"] + lp18["no_judge"]["tout"]))
cv = dict((a, tuple(int(v) for v in (x, y, x2, y2))) for a, x, y, x2, y2 in re.findall(r"\| (\w+) \| (\d+)/(\d+), p=[\d.]+ \| (\d+)/(\d+), p=[\d.]+ \|\n", rep))
T("control vs No-Semantic", rf"Against \cnosem{{}} the differences are not significant either (\pval{{{mp(cv['no_semantic'][0], cv['no_semantic'][1], 3)}}} and \pval{{{mp(cv['no_semantic'][2], cv['no_semantic'][3])}}})")
T("control vs Binary-Only", rf"Against \cbin{{}} it has {kco[3] - BO['co']} correct fixes more ({cv['binary_only'][3]} bugs repaired only by the control, {cv['binary_only'][2]} only by \cbin{{}}; \pval{{{mp(cv['binary_only'][2], cv['binary_only'][3])}}})")
T("RQ4 answer", rf"repair {NJ['co'] - kco[3]} bugs fewer than the four-iteration loop without the Judge ({kco[3]} against {NJ['co']} correct), for \${fmt(CR['usd'])} against \${CJ['usd']}, or \${fmt(CE['usd'])} when each bug stops at its first test-passing patch, and {F['co'] - kco[3]} fewer than the full loop, which costs \${CF['usd']}")
T("conclusion: control", rf"come within {NJ['co'] - kco[3]} correct fixes of the loop without the Judge and within {F['co'] - kco[3]} of the full loop")
T("conclusion: ablation", rf"loses {d_bo} correct fixes, the one difference that survives adjustment for multiple comparisons, ")
fc = fig_source("fig:control")
C("control figure: curves", re.findall(r"coordinates \{([^}]*)\};", fc) == [" ".join(f"({i + 1},{v})" for i, v in enumerate(k)) for k in (kpl, kco)])
C("control figure: reference lines", re.findall(r"domain=1:4\] \{(\d+)\};", fc) == [str(v) for v in (F['pl'], F['co'], NJ['pl'], NJ['co'])])
T("control figure caption", rf"the reference lines are \cfull{{}} ({F['pl']} plausible, {F['co']} correct) and \cnoj{{}} ({NJ['pl']}, {NJ['co']})")
T("control table caption", rf"compared with \cfull{{}} ({F['pl']} plausible, {F['co']} correct) and \cnoj{{}} ({NJ['pl']} plausible, {NJ['co']} correct)")
CONF5 = ("Full", "No-Semantic", "Binary-Only", "No-Judge", "Resample-4")
C("ablation figure", re.findall(r"coordinates \{([^}]*)\};", fig_source("fig:ablation")) == [" ".join(f"({nm},{v})" for nm, v in zip(CONF5, vals)) for vals in ([arms[a]["pl"] for a in ARMS] + [kpl[3]], [arms[a]["co"] for a in ARMS] + [kco[3]])])

# ── labels and consistency ────────────────────────────────────────────────
ident = R(r"- plausible records: (\d+); distinct patch texts: (\d+); texts recurring in two or more configurations: (\d+) \((\d+) records\)")
T("identical texts", rf"the {ident[0]} plausible records of the four configurations contain {ident[1]} distinct patch texts, {ident[2]} of which recur in two or more configurations ({ident[3]} records), and no recurring text carries two labels")
C("no recurring text carries two labels", "recurring texts whose final labels differ between configurations: none" in rep)
C("plausible records of the four configurations", int(ident[0]) == sum(a["pl"] for a in arms.values()))
ctlrec = sum(int(p_[3]) for p_ in passes)
T("patch records in all", rf"{th(int(ident[0]) + ctlrec)} patch records in all")
agr = re.findall(r"textually identical to an independently labelled arm patch for (\d+) bugs, label agreement (\d+)/(\d+); disagreements: ([^;]*); plausible patches with a recorded execution-based re-verification: (\d+)", rep)
assert len(agr) == 4
n_dis = sum(len(a[3].split("), ")) for a in agr)
first_labelled = sum(int(re.search(r"'verification': (\d+)", p_[5]).group(1)) for p_ in passes) + n_dis
T("control label agreement", rf"{sum(int(a[0]) for a in agr)} of the {first_labelled} control records labelled when the control was run are textually identical to a configuration patch that was labelled independently of the control; the control labels agree with the final configuration labels on {sum(int(a[1]) for a in agr)} of them, and the {WORDS[n_dis]} disagreements are two texts")
T("control: execution-based re-verification", rf"for {sum(int(a[4]) for a in agr)} of the {first_labelled} patch records they then had, an execution-based re-verification")
k2 = R(r"Independent review 2 \(blind\): n=(\d+), agreement=([\d.]+)%, κ=([\d.]+) \[95% bootstrap CI ([\d.]+), ([\d.]+)\], disagreements=(\d+)")
k3 = R(r"Independent review 3 \(blind\): n=(\d+), agreement=([\d.]+)%, κ=([\d.]+) \[95% bootstrap CI ([\d.]+), ([\d.]+)\], disagreements=(\d+)")
T("blind passes", rf"on {int(k2[0]) - int(k2[5])} of {k2[0]} patches ($\kappa={fmt(k2[2])}$, 95\% bootstrap interval ${k2[3]}$ to ${k2[4]}$; \citealp{{cohen1960}}) and with the pass-3 labels on {int(k3[0]) - int(k3[5])} of {k3[0]} ($\kappa={fmt(k3[2])}$, ${k3[3]}$ to ${k3[4]}$)")
exc = R(r"Bugs whose blind passes reviewed the patch of another execution, excluded here: (\d+) \(([^)]*)\)")
C("patches left out of the blind-pass figures: eight of the re-execution and eight of the Mockito bugs", int(exc[0]) == 16 and sum(x.startswith("Mockito") for x in exc[1].split(", ")) == 8 and int(k3[0]) + 16 == F["pl"])
n_re = int(exc[0]) - sum(x.startswith("Mockito") for x in exc[1].split(", "))
re_pl = int(re.search(r"- re-execution: valid executions \d+, plausible (\d+)", rep).group(1))
T("blind passes and the re-execution", rf"Of the {re_pl} plausible patches of the re-execution, {WORDS[re_pl - n_re]} have the text these passes read. Of the {WORDS[n_re]} others")
C("Closure-9 and Lang-16 are two of the four pass-3 disagreements", k3[5] == "4" and "Closure_9" in rep.split("Independent review 3 (blind)")[1].split("\n")[0] and "Lang_16" in rep.split("Independent review 3 (blind)")[1].split("\n")[0])
sv = {a: R(rf"- `{a}`: (\d+) patches logged plausible in the file[^;]*; canonical plausible patches whose text it reviewed: (\d+) of (\d+)") for a in ARMS}
svt = R(r"canonical plausible patches of the four configurations whose text the second verification reviewed: (\d+) of (\d+)")
T("second verification coverage", rf"Of the {svt[1]} canonical patches reported here it read the text of {svt[0]}: {sv['full'][1]} of the {sv['full'][2]} of \cfull{{}}, {sv['no_semantic'][1]} of the {sv['no_semantic'][2]} of \cnosem{{}}, {sv['binary_only'][1]} of the {sv['binary_only'][2]} of \cbin{{}} and {sv['no_judge'][1]} of the {sv['no_judge'][2]} of \cnoj")
ex9 = R(r"execution of the logged-plausible patches: \{'JDK 8 re-run of the relevant tests': (\d+), 'not re-run \(project could not be rebuilt\)': (\d+), 'token-identical to the developer fix, not re-executed': (\d+)\}")
T("second verification: Full", rf"the relevant tests were re-run for {ex9[0]} of the {sv['full'][0]} patches in its file; {ex9[2]} others are token-identical to the developer fix and were not re-executed, and {ex9[1]} Chart patches could not be rebuilt")
T("second verification: No-Semantic", rf"they were re-run for the {R(r"'Yes \(re-run\)': (\d+)")[0]} patches outside Chart")
T("labels given last: records", rf"Of the {BO['pl'] + NJ['pl']} plausible records of \cbin{{}} and \cnoj{{}}, ")

# ── re-execution, concurrent sessions ─────────────────────────────────────
v = re.findall(r"- ([^:\n]+): plausible=(\d+), correct=(\d+), pending=0; on the (\d+) re-executed bugs: plausible=(\d+), correct=(\d+); correct fixes against the reduced configurations \(full-only/other-only, McNemar\): no_semantic (\d+)/(\d+) p=[\d.]+; binary_only (\d+)/(\d+) p=[\d.]+; no_judge (\d+)/(\d+) p=[\d.]+; smallest Holm-adjusted value [\d.]+", rep)
assert len(v) == 3, len(v)


def cell(x, y):
    p_ = pt(x, y)
    return f"{x}/{y} ({p_})"


def hmin(v_):
    return min(holm([exact_p(v_[6], v_[7]), exact_p(v_[8], v_[9]), exact_p(v_[10], v_[11])]))


for v_, label in zip(v, ("Re-execution", "Earlier session", "Later session")):
    T(f"executions table, {label}", rf"{label} & {v_[4]} & {v_[5]} & {v_[1]} & {v_[2]} & {cell(v_[6], v_[7])} & {cell(v_[8], v_[9])} & {cell(v_[10], v_[11])} & {fmt(hmin(v_), 3)} \\")
e_, l_ = v[1], v[2]


def p2lt(x, y):
    return "$p<0.001$" if exact_p(x, y) < Fraction(1, 1000) and fmt(exact_p(x, y), 3) == "0.000" else rf"\pval{{{mp(x, y, 3) if exact_p(x, y) < Fraction(1, 100) else mp(x, y)}}}"


T("sensitivity 1: earlier session", rf"it has {e_[1]} plausible and {e_[2]} correct fixes ({p2lt(e_[6], e_[7])}, {p2lt(e_[8], e_[9])} and {p2lt(e_[10], e_[11])} against \cnosem{{}}, \cbin{{}} and \cnoj{{}})")
T("sensitivity 1: later session", rf"and with the later one {l_[1]} and {l_[2]} ({p2lt(l_[6], l_[7])}, {p2lt(l_[8], l_[9])} and {p2lt(l_[10], l_[11])})")
C("under each choice only the comparison with Binary-Only survives adjustment", all(sorted(holm([exact_p(x[6], x[7]), exact_p(x[8], x[9]), exact_p(x[10], x[11])]))[0] < Fraction(5, 100) < sorted(holm([exact_p(x[6], x[7]), exact_p(x[8], x[9]), exact_p(x[10], x[11])]))[1] and exact_p(x[8], x[9]) < exact_p(x[6], x[7]) for x in v))
T("threat: range over the three executions", rf"moves \cfull{{}} between {F['co']} and {l_[2]} correct fixes and leaves the comparison with \cbin{{}} the only one that survives adjustment")
C("the reported choice gives Full its lowest count", F["co"] == min(int(x[2]) for x in v))
strict = R(r"strict \(plausible in every execution\): plausible=(\d+)")
T("strict", rf"gives \cfull{{}} {strict[0]} plausible fixes instead of {F['pl']}")
d4 = R(r"- tested candidates in valid executions: (\d+); distinct texts: \d+; texts tested more than once: (\d+) \((\d+) candidates\)")
both = R(r"texts recorded both as passing and as failing: (\d+), of which (\d+) within valid executions \(([^)]*)\)")
T("appendix A: candidates", rf"{th(d4[0])} candidates were tested in valid executions; {th(d4[1])} texts were tested more than once ({th(d4[2])} candidates), and the recorded outcome is the same at every occurrence for all but {WORDS[int(both[1])]} of them. {WORDS[int(both[1]) - 1].capitalize()} are Mockito candidates")
C("the texts with two outcomes in valid executions", both[2] == "Chart_14, Mockito_5, Mockito_22, Mockito_24, Mockito_26")
cs = R(r"Valid executions of the two sessions on these bugs: (\d+), (\d+) tested candidates; candidates whose text was also tested in an execution outside the two sessions: (\d+) \((\d+) bugs\), same recorded outcome: (\d+)")
T("appendix A: concurrent sessions", rf"left {cs[0]} valid executions of the 52 bugs, with {cs[1]} tested candidates. For {cs[2]} of them, from {cs[3]} bugs, the same text was tested in an execution outside the two sessions, and {cs[4]} have the same recorded outcome there; the exception is the Chart-14 candidate. The {int(cs[1]) - int(cs[2])} others")
T("section 4.4: other candidates of the two sessions", rf"the same outcome for the {cs[4]} other candidates of these sessions")
T("appendix A: records that look normal", rf"The remaining {cs[0]} records look normal")
pr = re.findall(r"\| (re-execution vs full \d+_\d+|full \d+_\d+ vs full \d+_\d+) \| (\d+) \| (\d+) \| (\d+) \((\d+)%;[^|]*\) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|", rep)
assert len(pr) == 3
T("appendix A: three executions", rf"both valid for {pr[0][1]} of the 50 bugs and differ in the plausibility outcome of {WORDS[int(pr[0][3])]}; the later session and the re-execution, for {pr[1][1]} and {WORDS[int(pr[1][3])]}; the two concurrent sessions, for {pr[2][1]} and {WORDS[int(pr[2][3])]}. In each pair, every candidate text that both executions tested ({pr[0][7]}, {pr[1][7]} and {pr[2][7]} texts) has the same recorded outcome, and the first candidate has the same text for {pr[0][5]}, {pr[1][5]} and {pr[2][5]} bugs")
C("identical candidates have one outcome in each pair", all(p_[5] == p_[6] and p_[7] == p_[8] for p_ in pr))
T("appendix A: disagreement share", rf"disagree on the plausibility of {min(int(p_[4]) for p_ in pr)}\% to {max(int(p_[4]) for p_ in pr)}\% of these bugs")
T("section 4.4: plausibility differs", rf"for {WORDS[int(pr[0][3])]} and for {WORDS[int(pr[1][3])]} of the {pr[0][1]} bugs on which both are valid")
ex = re.findall(r"- (re-execution|full \d+_\d+): valid executions (\d+), plausible (\d+), tested candidates (\d+)", rep)
T("section 4.4: plausible patches on the 50 bugs", rf"the re-execution produced {ex[0][2]} plausible patches, against {ex[1][2]} in each concurrent session")
C("the two concurrent sessions have the same plausible count", ex[1][2] == ex[2][2])
fc = R(r"- re-execution against each other execution: [^\n]*\(range (\d+) to (\d+)\)\n- between two of the other executions: range (\d+) to (\d+) of (\d+) to (\d+) bugs")
fp = R(r"- first candidates that pass: re-execution (\d+);[^\n]*\(others: (\d+) to (\d+)\)")
T("appendix A: first candidates", rf"for {fc[0]} to {fc[1]} of the 47 to 50 bugs that both executed, against {fc[2]} to {fc[3]} between two of the other executions, and {fp[0]} of its first candidates pass, against {fp[1]} to {fp[2]}")
ps_ = R(r"- bugs compared per execution: (\d+) to (\d+); first Repair Agent prompt of equal size in every comparison: (\w+); first Judge prompt of equal size: (\d+)/(\d+)")
C("prompts of equal size in every comparison", ps_[2] == "yes" and ps_[3] == ps_[4])
T("appendix A: prompt sizes", rf"{ps_[0]} to {ps_[1]} bugs, depending on the execution), the recorded token count is identical")

# ── sensitivity: subsets ──────────────────────────────────────────────────
sb = {arm: R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+)/(\d+) \| [\d.]+ \| [\d.]+ \| [\d.]+ \| (\d+)/(\d+) \| [\d.]+ \|\n") for arm in ARMS[1:]}
sbf = R(r"\| full \| (\d+) \| (\d+) \| \| \| \| \| \| \|")
sbc = R(r"\| control \(best of 4\) \| (\d+) \| (\d+) \| (\d+)/(\d+) \| [\d.]+ \| \| \| (\d+)/(\d+) \| [\d.]+ \|")
n_sub = R(r"Paired set restricted to the other (\d+) bugs; McNemar exact against `full`, Holm over the three correct-fix comparisons.\n\n\| arm \| plausible \| correct \| correct: full-only/arm-only \| p \| p1 \|")[0]
hs2 = dict(zip(ARMS[1:], holm([exact_p(sb[a][2], sb[a][3]) for a in ARMS[1:]])))
T("subset table, Full", rf"\cfull{{}} & {sbf[0]} & {sbf[1]} & & & & & & \\")
for arm in ARMS[1:]:
    g = sb[arm]
    T(f"subset table, {arm}", rf"{MACRO[arm]} & {g[0]} & {g[1]} & {g[2]}/{g[3]} & {pt(g[2], g[3])} & {'$<$0.001' if exact_p(g[2], g[3]) / 2 < Fraction(1, 2000) else fmt(exact_p(g[2], g[3]) / 2, 3)} & {fmt(hs2[arm], 3)} & {g[4]}/{g[5]} & {pt(g[4], g[5])} \\")
T("subset table, control", rf"\cctrl{{}} & {sbc[0]} & {sbc[1]} & {sbc[2]}/{sbc[3]} & {pt(sbc[2], sbc[3])} & & & {sbc[4]}/{sbc[5]} & {pt(sbc[4], sbc[5])} \\")
g1, g2, g3 = sb["no_semantic"], sb["binary_only"], sb["no_judge"]
T("sensitivity 2: without the 52 bugs", rf"the {n_sub} remaining bugs give {sbf[1]} correct fixes for \cfull{{}} against {g1[1]}, {g2[1]} and {g3[1]} for \cnosem{{}}, \cbin{{}} and \cnoj{{}} (\pval{{{mp(g1[2], g1[3], 3)}}}, \pval{{{mp(g2[2], g2[3], 3)}}} and \pval{{{mp(g3[2], g3[3])}}}; Holm-adjusted ${fmt(hs2['no_semantic'])}$, ${fmt(hs2['binary_only'], 3)}$ and ${fmt(hs2['no_judge'])}$)")
T("appendix A: the remaining bugs", rf"On the {n_sub} remaining bugs the comparison with \cbin{{}} is significant after Holm adjustment and the two others are not")
C("... and the unadjusted values are smaller than on the full set for all three", all(exact_p(sb[a][2], sb[a][3]) < exact_p(st[a]["x"], st[a]["y"]) for a in ARMS[1:]) and hs2["binary_only"] < Fraction(5, 100) < min(hs2["no_semantic"], hs2["no_judge"]))
T("subset: plausible, Full against No-Judge", rf"the plausible counts of \cfull{{}} and \cnoj{{}} differ with \pval{{{mp(g3[4], g3[5], 3)}}}")
T("subset table caption", rf"on the {n_sub} bugs that the two concurrent sessions did not execute")
sub = R(r"on the 52 bugs themselves \(plausible / correct\): full (\d+) / (\d+), no_semantic (\d+) / (\d+), binary_only (\d+) / (\d+), no_judge (\d+) / (\d+), control (\d+) / (\d+)")
T("the 52 bugs themselves", rf"the four configurations have {sub[0]}, {sub[2]}, {sub[4]} and {sub[6]} plausible and {sub[1]}, {sub[3]}, {sub[5]} and {sub[7]} correct fixes, and the control {sub[8]} and {sub[9]}")
# without the bugs with an attempt that received no model output
no_out = R(r"executions with an attempt that received no model output: (\d+)")[0]
s2c = R(r"Sensitivity: the paired comparisons on the (\d+) evaluable bugs without the bugs whose canonical execution in some configuration has such an attempt \(([^)]*)\):\n\n- full vs no_semantic: correct (\d+) vs (\d+) [^\n]*\n- full vs binary_only: correct (\d+) vs (\d+) [^\n]*\n- full vs no_judge: correct (\d+) vs (\d+) ")
n_out_bugs = len(s2c[1].split(", "))
T("attempts without model output: executions", rf"{WORDS[int(no_out)].capitalize()} executions contain such an attempt")
T("attempts without model output: bugs", rf"repeats the comparisons without the {WORDS[n_out_bugs]} bugs")
T("sensitivity 4: without these bugs", rf"without the {WORDS[n_out_bugs]} bugs that have an attempt without model output in some configuration (Section~\ref{{sec:failure-modes}}), the discordant pairs against \cfull{{}} are {s2c[2]} and {s2c[3]} for \cnosem{{}} (\pval{{{mp(s2c[2], s2c[3])}}}), {s2c[4]} and {s2c[5]} for \cbin{{}} (\pval{{{mp(s2c[4], s2c[5], 3)}}}) and {s2c[6]} and {s2c[7]} for \cnoj{{}} (\pval{{{mp(s2c[6], s2c[7])}}})")
C("bugs left without them", int(s2c[0]) == N_BUGS - n_out_bugs)
# without the 15 Mockito bugs
sec = rep.split("## 14c.")[1].split("\n## ")[0]
m15 = {arm: R(rf"\| {arm} \| (\d+) \| (\d+) \| (\d+)/(\d+) \| [\d.]+ \| [\d.]+ \| (\d+)/(\d+) \| [\d.]+ \|", sec) for arm in ARMS[1:]}
m15f = R(r"\| full \| (\d+) \| (\d+) \| \| \| \| \| \|", sec)
on15 = R(r"on the 15 bugs themselves \(plausible / correct\): full (\d+) / (\d+); no_semantic (\d+) / (\d+); binary_only (\d+) / (\d+); no_judge (\d+) / (\d+)", sec)
hs3 = dict(zip(ARMS[1:], holm([exact_p(m15[a][2], m15[a][3]) for a in ARMS[1:]])))
a_, b__, c_ = m15["no_semantic"], m15["binary_only"], m15["no_judge"]
T("sensitivity 5: without the 15 Mockito bugs", rf"the {N_BUGS - 15} other bugs give {m15f[1]} correct fixes for \cfull{{}} against {a_[1]}, {b__[1]} and {c_[1]} (\pval{{{mp(a_[2], a_[3])}}}, \pval{{{mp(b__[2], b__[3], 3)}}} and \pval{{{mp(c_[2], c_[3])}}}; Holm-adjusted ${fmt(hs3['binary_only'], 3)}$ for \cbin{{}}); on the 15 bugs themselves the four configurations have {on15[1]}, {on15[3]}, {on15[5]} and {on15[7]}")
for where in ("They add ", ""):
    pass
T("threats: the 15 Mockito bugs", rf"They add {on15[0]}, {on15[2]}, {on15[4]} and {on15[6]} plausible and {on15[1]}, {on15[3]}, {on15[5]} and {on15[7]} correct fixes to the four configurations")
T("threats: the 15 Mockito bugs and the served model", rf"the four configurations have {on15[1]}, {on15[3]}, {on15[5]} and {on15[7]} correct fixes. The control")
C("counts on the two parts add up", all(int(m15[a][1]) + int(on15[2 * i + 3]) == arms[a]["co"] for i, a in enumerate(ARMS[1:])) and int(m15f[1]) + int(on15[1]) == F["co"])
T("offline review: patches before the Mockito bugs", rf"The review covers the {m15f[0]} plausible patches that the configuration had before the 15 Gradle-built Mockito bugs were executed (Section~\ref{{sec:benchmark}}); the {WORDS[int(on15[0])]} plausible patches of those bugs were not reviewed")

# ── false negatives ───────────────────────────────────────────────────────
fn = {}
for arm in ARMS:
    g = R(rf"\| {arm} \| [A-Za-z_0-9, ():]+ \| (\d+) \| (\d+) \| ([^|]*)\|\n")
    fn[arm] = (g[0], g[1], g[2].strip())
fc_ = R(r"\| control \(best of 4\) \| [A-Za-z_0-9, ]+ \| (\d+) \| (\d+) \| (\d+)/(\d+), p=([\d.]+)")


def xy(s_):
    return re.match(r"(\d+)/(\d+), p=", s_).groups()


a_, b__, c_ = xy(fn["no_semantic"][2]), xy(fn["binary_only"][2]), xy(fn["no_judge"][2])
T("false negatives, appendix", rf"gives {fn['full'][0]}, {fn['no_semantic'][0]}, {fn['binary_only'][0]} and {fn['no_judge'][0]} plausible and {fn['full'][1]}, {fn['no_semantic'][1]}, {fn['binary_only'][1]} and {fn['no_judge'][1]} correct fixes for the four configurations, and {fc_[0]} and {fc_[1]} for the control. The comparisons against \cfull{{}} become {a_[0]} against {a_[1]} discordant bugs (\pval{{{mp(*a_)}}}), {b__[0]} against {b__[1]} (\pval{{{mp(*b__, 3)}}}) and {c_[0]} against {c_[1]} (\pval{{{mp(*c_)}}}), and {fc_[2]} against {fc_[3]} for the control (\pval{{{mp(fc_[2], fc_[3])}}})")
T("sensitivity 3: false negatives", rf"gives {fn['full'][1]}, {fn['no_semantic'][1]}, {fn['binary_only'][1]} and {fn['no_judge'][1]} correct fixes (\pval{{{mp(*a_)}}}, \pval{{{mp(*b__, 3)}}} and \pval{{{mp(*c_)}}} against \cfull")
T("false negatives, threats", rf"gives {fn['full'][1]}, {fn['no_semantic'][1]}, {fn['binary_only'][1]} and {fn['no_judge'][1]} correct fixes for the four configurations and {fc_[1]} for the control")
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
T("first-attempt variation in the threats", rf"{min(disc):.1f}\% to {max(disc):.1f}\% of bugs between two configurations")

# ── offline review ────────────────────────────────────────────────────────
rev = {}
for model, name in (("deepseek_v4_flash_semantic", "DeepSeek V4 Flash"), ("gemini_3_5_flash_lite_semantic", r"\model{}"), ("claude_sonnet_5_5_semantic", "Claude Sonnet 5.5")):
    g = R(rf"\| {model} \| (\d+) \| (\d+) \| (\d+)/(\d+) \| (\d+)/(\d+) \| (\d+)/(\d+) \| ([\d.-]+) \[([\d.-]+), ([\d.-]+)\] \|")
    rev[model] = g
    C(f"offline review, {model}: the vetoes are the overfitting and the correct patches vetoed", int(g[1]) == int(g[2]) + int(g[4]) == int(g[7]) and g[6] == g[2])
ds, gm, cl = (rev[m_] for m_ in ("deepseek_v4_flash_semantic", "gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"))
T("offline review: first two reviewers", rf"DeepSeek vetoes {ds[1]} patches, of which {ds[2]} are overfitting and {ds[4]} correct; \model{{}} vetoes {gm[1]}, of which {gm[2]} are overfitting and {gm[4]} correct; Cohen's $\kappa$ against the verified labels is ${fmt(ds[8])}$ and ${fmt(gm[8])}$")
dsline = rep.split("| deepseek_v4_flash_semantic |")[1].split("\n")[2]
C("the DeepSeek line of wrongly vetoed patches", dsline.strip().startswith("- vetoed, correct:"))
T("offline review: DeepSeek and token-identical patches", rf"{WORDS[dsline.count('[Correct (identical)]')].capitalize()} of the {ds[4]} correct patches DeepSeek vetoes are token-identical to the developer fix")
C("Sonnet vetoes no token-identical patch", "[Correct (identical)]" not in rep.split("| claude_sonnet_5_5_semantic |")[1].split("\n")[2])
T("offline review: Sonnet", rf"It vetoes {cl[1]} patches, of which {cl[2]} are overfitting and {cl[4]} correct ($\kappa={fmt(cl[8])}$, interval ${cl[9]}$ to ${cl[10]}$)")
left, left_ok = int(cl[0]) - int(cl[1]), int(cl[5]) - int(cl[4])
T("offline review: as a filter", rf"Used as a filter on these {cl[0]} patches, its vetoes would raise precision from {pct(cl[5], cl[0])}\% to {pct(left_ok, left)}\% ({left_ok} of {left}) at the cost of {cl[4]} of their {cl[5]} correct fixes")
T("offline review: contribution", rf"detect {ds[2]} and {gm[2]} of {ds[3]} overfitting patches while wrongly vetoing {ds[4]} and {gm[4]} correct ones ($\kappa={fmt(ds[8])}$ and ${fmt(gm[8])}$), and Claude Sonnet~5.5 detects {cl[2]} of {cl[3]} while wrongly vetoing {cl[4]} of {cl[5]} ($\kappa={fmt(cl[8])}$")
T("offline review: abstract", rf"agreement beyond chance is not established for two (Cohen's kappa {fmt(ds[8])} and {fmt(gm[8])}), and Claude Sonnet 5.5 catches half the overfitting patches (kappa {fmt(cl[8])})")
C("Sonnet catches 'half' of the overfitting patches, at 'about one correct fix in twenty'", 2 * int(cl[2]) == int(cl[3]) and 17 <= int(cl[5]) / int(cl[4]) <= 23)
T("offline review table caption", rf"Offline LLM review of the {cl[0]} plausible patches")

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
for a1, a2 in (("full", "no_semantic"), ("full", "binary_only"), ("full", "no_judge"), ("full", "control"), ("no_judge", "control")):
    g = ci[(a1, a2, "correct")]
    T(f"intervals table, {a1} minus {a2}", rf"{MC[a1]} minus {MC[a2]} & ${g['d']}$ & ${g['lo']}$ to ${g['hi']}$ & ${g['dp']}$ & ${g['lop']}$ to ${g['hip']}$ \\")


def ri(s_):
    """a bound in bugs, rounded to the nearest whole bug (half away from zero)"""
    return int(Decimal(s_).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def sg(n_):
    return f"${n_:+d}$"


cb, cj, cfc, cjc = (ci[k_] for k_ in (("full", "binary_only", "correct"), ("full", "no_judge", "correct"), ("full", "control", "correct"), ("no_judge", "control", "correct")))
T("intervals in RQ3", rf"{d_bo} fixes for \cbin{{}}, with an interval from {ri(cb['lo'])} to {ri(cb['hi'])}, and {d_nj} for \cnoj{{}}, with an interval from a loss of {-ri(cj['lo'])} fixes to a gain of {ri(cj['hi'])}")
T("RQ3 answer: interval", rf"runs from a loss of {-ri(cj['lo'])} fixes to a gain of {ri(cj['hi'])}: the experiment establishes neither")
T("contribution 3: review", rf"that removing the Judge costs {d_nj} (95\% confidence interval {sg(ri(cj['lo']))} to {sg(ri(cj['hi']))}), which cannot be distinguished")
T("contribution 3: control", rf"obtain {NJ['co'] - kco[3]} correct fixes fewer than the loop without the Judge (interval {sg(ri(cjc['lo']))} to {sg(ri(cjc['hi']))};")
T("RQ4: interval against No-Judge", rf"cannot distinguish from zero (95\% confidence interval {sg(ri(cjc['lo']))} to {sg(ri(cjc['hi']))}, Table~\ref{{tab:intervals}})")
T("RQ4: interval against Full", rf"the interval of the difference in correct fixes, {sg(ri(cfc['lo']))} to {sg(ri(cfc['hi']))}, is compatible with no advantage")
T("RQ4 answer: intervals", rf"their 95\% confidence intervals, {sg(ri(cjc['lo']))} to {sg(ri(cjc['hi']))} and {sg(ri(cfc['lo']))} to {sg(ri(cfc['hi']))} correct fixes")
C("RQ4 answer: 'a gain two to three times the one observed'", 2 <= ri(cjc['hi']) / (NJ['co'] - kco[3]) <= 3 and 2 <= ri(cfc['hi']) / (F['co'] - kco[3]) <= 3)
C("RQ4: 'one twice as large as observed'", 1.9 <= ri(cfc['hi']) / (F['co'] - kco[3]) <= 2.2)
T("discussion: interval", rf"({d_nj} fixes in {N_BUGS}, with a 95\% confidence interval from {sg(ri(cj['lo']))} to {sg(ri(cj['hi']))})")
T("conclusion: review", rf"while the loop without the Judge loses {d_nj} (95\% confidence interval {sg(ri(cj['lo']))} to {sg(ri(cj['hi']))}), a difference that the experiment does not establish")
C("the intervals of the two comparisons with the Judge include zero, that of Binary-Only does not", float(cj['lo']) < 0 < float(cj['hi']) and float(ci[("full", "no_semantic", "correct")]['lo']) < 0 and float(cb['lo']) > 0)

# ── first attempts and the temperature requested (report section 16) ─────
sec16 = rep.split("## 16.")[1].split("\n## ")[0]
runs16 = re.findall(r"\| (\w+) \| ([\d.]+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\n", sec16)
assert len(runs16) == 8 and [r_[0] for r_ in runs16[:4]] == list(ARMS)
C("every first attempt made its usual request", all(r_[2] == r_[3] == str(N_BUGS) for r_ in runs16))
req = [r_[1] for r_ in runs16]
C("the eight runs requested 0.1 five times, 0.45 twice and 0.85 once", (req.count("0.1"), req.count("0.45"), req.count("0.85")) == (5, 2, 1))
C("the first attempts of the configurations are those of the replication table", [(r_[4], r_[5]) for r_ in runs16[:4]] == [(str(p1[i]), str(c1[i])) for i in range(4)])
C("the passes are those of the control table", [(r_[4], r_[5]) for r_ in runs16[4:]] == [(p_[3], p_[4]) for p_ in passes])
T("first attempts: the control passes", rf"they produce {ppl[0]}, {ppl[1]}, {ppl[2]} and {ppl[3]} plausible and {pco[0]}, {pco[1]}, {pco[2]} and {pco[3]} correct patches, inside the spread of the four configurations")
C("... inside the spread of the four configurations", min(p1) <= min(ppl) and max(ppl) <= max(p1) and min(c1) <= min(pco) and max(pco) <= max(c1))
o16 = R(r"over the (\d+) runs: plausible at the first attempt (\d+) to (\d+), correct (\d+) to (\d+)")
T("appendix C: the eight runs", rf"{o16[1]} to {o16[2]} plausible and {o16[3]} to {o16[4]} correct patches at the first attempt")
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
T("appendix C: same text over all pairs", rf"Over the {al[0]} pairs of runs, the candidates of a bug have the same text in {al[3]}\% of the comparisons, between {al[4]}\% and {al[5]}\% per pair")
C("the share does not fall as the requested temperature rises", float(grp[('0.1', '0.1')][3]) <= min(float(grp[k_][3]) for k_ in grp if k_ != ('0.1', '0.1')))

# ── kinds of correct label, and the comparisons without alternative fixes (section 17) ──
sec17 = rep.split("## 17.")[1].split("\n## ")[0]
kd = {r_[0]: [int(v_) for v_ in r_[1:]] for r_ in re.findall(r"\| (\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\n", sec17)}
assert set(kd) == set(ARMS) | {"control"}        # plausible, identical, equivalent, alternative, no kind, overfitting, identical or equivalent
C("kinds: the rows add up to the headline counts", all(kd[a][1] + kd[a][2] + kd[a][3] + kd[a][4] == arms[a]["co"] and kd[a][0] == arms[a]["pl"] for a in ARMS) and kd["control"][0] == kpl[3] and sum(kd["control"][1:5]) == kco[3])
C("kinds: the split of Full is the one given in RQ1", (kd["full"][1], kd["full"][2], kd["full"][3]) == (int(split[2]), int(split[1]), int(split[0])))
kf, kb, kj, kc, kn = (kd[a] for a in ("full", "binary_only", "no_judge", "control", "no_semantic"))
T("kinds per configuration", rf"Of the {F['co']} correct fixes of \cfull{{}}, {kf[1]} are identical, {kf[2]} equivalent and {kf[3]} alternative; \cbin{{}} has {kb[1]}, {kb[2]} and {kb[3]}, \cnoj{{}} {kj[1]}, {kj[2]} and {kj[3]}, and the control {kc[1]}, {kc[2]} and {kc[3]}, so {kf[3] - kb[3]} of the {d_bo} fixes by which \cbin{{}} trails are a difference in alternative fixes")
byk = R(r"full minus binary_only, by kind: identical ([+-]\d+), equivalent ([+-]\d+), alternative ([+-]\d+), all correct ([+-]\d+)", sec17)
C("... as the report gives the difference by kind", (int(byk[2]), int(byk[3])) == (kf[3] - kb[3], d_bo))
alt = kf[3] - kb[3]
T("abstract: alternative fixes", rf"with alternative fixes left out ({kf[6]} against {kb[6]}) the difference is not significant")
T("contribution 3: alternative fixes", rf"the only difference that survives multiplicity correction, and one that is no longer significant when alternative fixes are left out ({kf[6]} against {kb[6]}); that removing the Judge")
T("RQ3 answer: alternative fixes", rf"{WORDS_CAP[alt]} of the {d_bo} are a surplus of alternative fixes ({kf[3]} against {kb[3]}): when alternative fixes are not counted, the difference keeps its direction ({kf[6]} against {kb[6]}) and is not significant")
T("conclusion: alternative fixes", rf"the one difference that survives adjustment for multiple comparisons, though not when alternative fixes are left out ({kf[6]} against {kb[6]}), while the loop without the Judge")
T("kinds: No-Semantic (section 4.5)", rf"where {kn[4]} of the {NS['co']} correct patches carry the label correct without a kind")
T("kinds: No-Semantic (RQ3)", rf"For \cnosem{{}} the kind was not recorded for {kn[4]} of the {NS['co']} correct patches")
C("kinds are recorded for every other configuration and for the control", all(kd[a][4] == 0 for a in ("full", "binary_only", "no_judge", "control")))
sr = {r_[0]: r_[1:] for r_ in re.findall(r"\| full vs (\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|", sec17)}
assert set(sr) == {"binary_only", "no_judge", "control"}
C("strict counts are the identical and equivalent patches", int(sr["binary_only"][0]) == kf[6] and int(sr["binary_only"][1]) == kb[6] and int(sr["no_judge"][1]) == kj[6] and int(sr["control"][1]) == kc[6])
T("without alternative fixes", rf"With the identical and equivalent patches alone, \cfull{{}} has {kf[6]} against {kb[6]} for \cbin{{}} ({sr['binary_only'][2]} against {sr['binary_only'][3]} discordant bugs; \pval{{{mp(sr['binary_only'][2], sr['binary_only'][3])}}}), and no comparison is significant")
C("without alternative fixes: no comparison is significant", all(exact_p(sr[a][2], sr[a][3]) > Fraction(5, 100) for a in sr) and int(sr["binary_only"][2]) > int(sr["binary_only"][3]))
ls = R(r"- full vs binary_only: (\d+) bugs, (\d+) / (\d+), only first (\d+), only second (\d+), p=([\d.]+)", sec17)
C("later attempts without alternative fixes: the bugs are those of the later-attempts table", int(ls[0]) == fb[0])
T("without alternative fixes: later attempts", rf"the later attempts give {ls[1]} against {ls[2]} for \cfull{{}} and \cbin{{}} (\pval{{{mp(ls[3], ls[4])}}})")
tw = R(r"patch texts that carry two kinds of correct label \(in a configuration and in a control pass\): (\d+) \(([^)]*)\)", sec17)
tw_names = [x.split(":")[0].replace("_", "-") for x in tw[1].split("; ")]
T("texts with two kinds", rf"{WORDS_CAP[int(tw[0])]} patch texts carry one kind in the configurations and another in a control pass ({', '.join(tw_names[:-1])} and {tw_names[-1]}); counting them either way leaves the comparison with \cbin{{}} between \pval{{{fmt(min(float(sr['binary_only'][5]), float(sr['binary_only'][6])))}}} and \pval{{{fmt(max(float(sr['binary_only'][4]), float(sr['binary_only'][5]), float(sr['binary_only'][6])))}}}")
ph = dict((a, (x, y, p_, h_)) for a, x, y, p_, h_ in re.findall(r"(\w+) (\d+)/(\d+), p=([\d.]+), Holm ([\d.]+)", sec17))
C("plausible, Holm over the three: as the report gives it", fmt(holm([exact_p(st[a]["xp"], st[a]["yp"]) for a in ARMS[1:]])[1], 4) == ph["binary_only"][3] and (int(ph["binary_only"][0]), int(ph["binary_only"][1])) == (b["xp"], b["yp"]))
T("plausible counts involve no label", rf"{F['pl']} against {BO['pl']} (\pval{{{mp(b['xp'], b['yp'], 3)}}}, and ${fmt(ph['binary_only'][3], 3)}$ after Holm adjustment over the three comparisons), and, on the bugs whose first attempt failed in both configurations, {fb[1]} against {fb[2]} plausible patches from the later attempts (\pval{{{mp(fb[3], fb[4], 3)}}})")
C("the plausible difference survives Holm adjustment", float(ph["binary_only"][3]) < 0.05)

# ── the reviewers as filters and on the same patches (report section 10) ──
flt = {}
for model in rev:
    flt[model] = R(rf"\| {model} \| (\d+) \| ([\d.]+)% \| (\d+)/(\d+) \| (\d+)/(\d+) \| (\d+) \| (\d+) \(([\d.]+)%\) \| ([\d.]+)% \|")
fd, fg, fcl = (flt[m_] for m_ in ("deepseek_v4_flash_semantic", "gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"))
C("filters: the rows are those of the review table", all((flt[m_][0], flt[m_][2], flt[m_][4]) == (rev[m_][0], rev[m_][2], rev[m_][4]) for m_ in rev))
T("offline review: the first two as filters", rf"As filters they would move precision from {fd[1]}\% to {fd[9]}\% and from {fg[1]}\% to {fg[9]}\%, less than one point, at the cost of {fd[4]} and {fg[4]} correct fixes")
C("... 'less than one point'", 0 < float(fd[9]) - float(fd[1]) < 1 and 0 < float(fg[9]) - float(fg[1]) < 1)
T("offline review: what Sonnet leaves", rf"{fcl[7]} of the {fcl[6]} patches it keeps ({fcl[8]}\%) are still overfitting")
C("... consistent with the filter sentence", (int(fcl[6]), fcl[9]) == (left, pct(left_ok, left)))
T("RQ5 answer: the two smaller models", rf"as filters they would change precision by less than one point while discarding {fd[4]} and {fg[4]} correct fixes")
blkA = rep.split("Matched set, the patches scored for every reviewer")[1].split("Matched set, the same without")[0]
blkB = rep.split("Matched set, the same without the multi-file patches")[1].split("\n## ")[0]
mA = re.match(r": (\d+) patches \((\d+) overfitting, (\d+) correct\)", blkA).groups()
mB = re.match(r": (\d+) patches \((\d+) overfitting, (\d+) correct\)", blkB).groups()
rowA = {m_: R(rf"\| {m_} \| (\d+)/(\d+) \| (\d+)/(\d+) \| ([\d.-]+) \| ([\d.]+)% \| ([\d.]+)% \|", blkA) for m_ in rev}
rowB = {m_: R(rf"\| {m_} \| (\d+)/(\d+) \| (\d+)/(\d+) \| ([\d.-]+) \| ([\d.]+)% \| ([\d.]+)% \|", blkB) for m_ in rev}
da, ga, ca = (rowA[m_] for m_ in ("deepseek_v4_flash_semantic", "gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"))
db_, gb_, cb_ = (rowB[m_] for m_ in ("deepseek_v4_flash_semantic", "gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic"))
T("offline review: the same patches for all three", rf"The three reviewers were scored on {ds[0]}, {gm[0]} and {cl[0]} patches. On the {mA[0]} that all three judged on the canonical text ({mA[1]} overfitting, {mA[2]} correct), DeepSeek, \model{{}} and Claude Sonnet~5.5 catch {da[0]}, {ga[0]} and {ca[0]} overfitting patches and wrongly veto {da[2]}, {ga[2]} and {ca[2]} correct ones ($\kappa={fmt(da[4])}$, ${fmt(ga[4])}$ and ${fmt(ca[4])}$)")
T("offline review: without the multi-file patches", rf"Without the {WORDS[int(mA[0]) - int(mB[0])]} multi-file patches of that set, of which the reviewers saw one file, the counts are the same except that DeepSeek wrongly vetoes {db_[2]}")
C("... the other counts are the same", (db_[0], gb_[0], cb_[0], gb_[2], cb_[2]) == (da[0], ga[0], ca[0], ga[2], ca[2]) and db_[2] != da[2])
C("the ranking of the reviewers is the same on the matched set", float(ca[4]) > max(float(da[4]), float(ga[4])) and float(cl[8]) > max(float(ds[8]), float(gm[8])))
C("abstract, conclusion: the intervals of the two smaller reviewers include zero", float(ds[9]) < 0 < float(ds[10]) and float(gm[9]) < 0 < float(gm[10]) and float(cl[9]) > 0)

# ── cost at smaller budgets and at equal spending (report section 18) ─────
sec18 = rep.split("## 18.")[1].split("\n## ")[0]
bud = {}
for name, k_, pl_, co_, tin, tout, usd_ in re.findall(r"\| ([\w, ]+?) \| (\d) \| (\d+) \| (\d+) \| ([\d,]+) \| ([\d,]+) \| \$([\d.]+) \| \$[\d.]+ \|", sec18):
    bud[(name, int(k_))] = dict(pl=int(pl_), co=int(co_), usd=usd_)
    C(f"budget table: cost of {name} at k={k_} follows from its tokens",
      fmt((int(tin.replace(",", "")) * PRICE_IN + int(tout.replace(",", "")) * PRICE_OUT) / 10 ** 6) == usd_)
assert len(bud) == 24
C("budget table: the full budget is the table of costs", all(bud[(a, 4)]["usd"] == cost[a]["usd"] and bud[(a, 4)]["co"] == arms[a]["co"] for a in ARMS)
  and bud[("control, as run", 4)]["usd"] == fmt(CR["usd"]) and bud[("control, early stop", 4)]["usd"] == fmt(CE["usd"]))
C("budget table: the control at k passes is the control table", [bud[("control, as run", k_)]["co"] for k_ in (1, 2, 3, 4)] == kco)
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
assert len(sh) == 6                                  # same first candidate, fails in both, plausible a/b, only a/b, correct a/b, only a/b
sb, sj, sn = sh[("full", "binary_only")], sh[("full", "no_judge")], sh[("full", "no_semantic")]
C("shared first candidate: 'none only by Binary-Only', '15 plausible patches each'", sb[9] == 0 and sj[2] == sj[3])
T("shared first candidate: Full and Binary-Only", rf"\cfull{{}} and \cbin{{}} share a failed first candidate on {sb[1]} bugs, on which their later attempts yield {sb[2]} against {sb[3]} plausible and {sb[6]} against {sb[7]} correct patches ({sb[8]} bugs fixed only by \cfull{{}}, none only by \cbin{{}}; \pval{{{mp(sb[8], sb[9])}}})")
T("shared first candidate: the two other pairs", rf"\cfull{{}} and \cnoj{{}} share one on {sj[1]} bugs, with {sj[2]} plausible patches each and {sj[6]} against {sj[7]} correct ones (\pval{{{mp(sj[8], sj[9])}}}), and \cfull{{}} and \cnosem{{}} on {sn[1]}, with {sn[6]} against {sn[7]} correct ones (\pval{{{mp(sn[8], sn[9])}}})")
C("... 'the direction they have on all bugs', 'too few bugs to be tested'", all(v[6] > v[7] and exact_p(v[8], v[9]) > Fraction(5, 100) for v in (sb, sj, sn)))
sec19b = rep.split("The same comparison on the bugs whose first candidates differ and both fail")[1].split("\n## ")[0]
ob = [int(v) for v in R(r"\| full vs binary_only \| (\d+) \| (\d+) / (\d+) \| \d+/\d+, p=[\d.]+ \| (\d+) / (\d+) \| \d+/\d+, p=[\d.]+ \|", sec19b)]
C("shared first candidate: the two parts make up the bugs of the later-attempts table", sb[1] + ob[0] == fb[0] and sb[2] + ob[1] == fb[1] and sb[3] + ob[2] == fb[2] and sb[6] + ob[3] == fb[5] and sb[7] + ob[4] == fb[6])
T("shared first candidate: the other bugs", rf"on the {ob[0]} other bugs of Table~\ref{{tab:later}}, where their failed first candidates differ, the counts are {ob[1]} against {ob[2]} and {ob[3]} against {ob[4]}")
T("threats: shared first candidate", rf"on the {min(sb[1], sj[1], sn[1])} to {max(sb[1], sj[1], sn[1])} bugs on which two configurations happen to share a failed first candidate")

# ── three endpoints (report section 20) ───────────────────────────────────
sec20 = rep.split("## 20.")[1].split("\ncanonical per-bug tables")[0]
e20 = {a: (int(pl_), rng, int(co_), int(rec_), els, int(now_)) for a, pl_, rng, co_, rec_, els, now_ in
       re.findall(r"\| (\w+) \| (\d+) \| ([\d to]+) \| (\d+) \| (\d+) \| ([^|]*) \| (\d+) \|", sec20)}
assert set(e20) == set(ARMS) | {"control"}
ns20 = e20["no_semantic"]
els20 = int(ns20[4].split(" ")[0])
lo20, hi20 = ns20[1].split(" to ")
C("endpoints: the kinds of No-Semantic add up", ns20[3] + els20 + ns20[5] == NS["co"] and els20 + ns20[5] == kn[4])
C("endpoints: the other configurations have every kind recorded", all(e20[a][3] == e20[a][2] and e20[a][5] == 0 for a in e20 if a != "no_semantic"))
C("endpoints: the lower ends are the counts without the texts that carry two kinds", e20["full"][1].split(" to ")[0] == str(kf[6]) and e20["binary_only"][1].split(" to ")[0] == str(kb[6]))
T("endpoints: No-Semantic", rf"For {els20} of them the same patch text carries a kind in another configuration or in a control pass; the {ns20[5]} others leave its count of identical or equivalent patches between {lo20} and {hi20}, a range too wide for a comparison with the {kf[6]} of \cfull{{}}")
T("endpoints table: caption", rf"For \cnosem{{}} the kind of {ns20[5]} correct patches is recorded nowhere, which leaves a range")
T("endpoints table, full", rf"\cfull{{}} & {F['pl']} & & {kf[6]} & & {F['co']} & \\")
T("endpoints table, no_semantic", rf"\cnosem{{}} & {NS['pl']} & {pt(n['xp'], n['yp'])} & {lo20} to {hi20} & & {NS['co']} & {pt(n['x'], n['y'])} \\")
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
order = ("deepseek_v4_flash_semantic", "gemini_3_5_flash_lite_semantic", "claude_sonnet_5_5_semantic")
cd, cg, cs = (cm[m_] for m_ in order)


def kap(g):
    lo = ("$-" + g[9][1:] + "$") if g[9].startswith("-") else g[9]
    return rf"{fmt(g[8])} [{lo}, {g[10]}]"


T("offline review table: patches scored", rf"Patches scored & {cd['n']} & {cg['n']} & {cs['n']} \\")
T("offline review table: overfitting patches", rf"Overfitting: vetoed, kept & {cd['tp']}, {cd['fn']} & {cg['tp']}, {cg['fn']} & {cs['tp']}, {cs['fn']} \\")
T("offline review table: correct patches", rf"Correct: vetoed, kept & {cd['fp']}, {cd['tn']} & {cg['fp']}, {cg['tn']} & {cs['fp']}, {cs['tn']} \\")
for label, key in (("Sensitivity", "sens"), ("Specificity", "spec"), ("Veto precision", "prec")):
    T(f"offline review table: {label.lower()}", label + " & " + " & ".join(rf"{c_[key][0]}\% [{c_[key][1]}, {c_[key][2]}]" for c_ in (cd, cg, cs)) + r" \\")
T("offline review table: kappa", r"$\kappa$ vs.\ labels & " + " & ".join(kap(rev[m_]) for m_ in order) + r" \\")
T("offline review: sensitivity of the first two", rf"their sensitivity, {fmt(cd['sens'][0], 0)}\% and {fmt(cg['sens'][0], 0)}\%, has intervals that reach {fmt(cd['sens'][2], 0)}\% and {fmt(cg['sens'][2], 0)}\%")
T("RQ5 answer: wording", r"For the two smaller models, agreement with the labels beyond chance is not established")
prs = {(a1, a2): tuple(int(v) for v in vals) for a1, a2, *vals in
       re.findall(r"- (\w+) vs (\w+): overfitting vetoed (\d+)/(\d+), p=[\d.]+; correct vetoed (\d+)/(\d+), p=[\d.]+; agrees with the label (\d+)/(\d+), p=[\d.]+", rep)}
assert set(prs) == {(order[0], order[1]), (order[0], order[2]), (order[1], order[2])}
dg, dc, gc = prs[(order[0], order[1])], prs[(order[0], order[2])], prs[(order[1], order[2])]
C("pairs of reviewers: 'DeepSeek none that Claude Sonnet 5.5 keeps'", dc[0] == 0)
T("pairs of reviewers: overfitting patches", rf"Claude Sonnet~5.5 vetoes {dc[1]} overfitting patches that DeepSeek keeps, and DeepSeek none that Claude Sonnet~5.5 keeps (McNemar exact test, \pval{{{mp(dc[0], dc[1], 3)}}}); against \model{{}} the counts are {gc[1]} and {gc[0]} (\pval{{{mp(gc[0], gc[1], 3)}}})")
T("pairs of reviewers: correct patches", rf"DeepSeek and \model{{}} differ ({dg[2]} against {dg[3]} vetoed by one of them only; \pval{{{mp(dg[2], dg[3], 3)}}}), and neither differs significantly from Claude Sonnet~5.5 (\pval{{{mp(dc[2], dc[3])}}} and \pval{{{mp(gc[2], gc[3])}}})")
C("... as stated", exact_p(dg[2], dg[3]) < Fraction(5, 100) and exact_p(dc[2], dc[3]) > Fraction(5, 100) and exact_p(gc[2], gc[3]) > Fraction(5, 100))

# ── statements that repeat a constant of the analysis or a count pinned elsewhere ─────────
T("cost table caption: prices", r"USD at the list prices of the model, 0.30 per million input tokens and 2.50 per million output tokens")
T("cost paragraph: the flat rate of the harness", r"at a flat rate of 0.35 per million tokens")
T("Judge: one file of a multi-file candidate", rf"the review of the {mf[0]} multi-file bugs is therefore partial")

# ── the failure-injection tests and the limits of the prompts (read in the repository, when the checker runs inside it) ──
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tests_py, removals_py, harness_py = (os.path.join(root, *p_) for p_ in (("tests", "test_safeguards.py"), ("tests", "remove_each_safeguard.py"), ("src", "agentic_apr.py")))
if all(os.path.exists(p_) for p_ in (tests_py, removals_py, harness_py)):
    tests_src, harness_src = open(tests_py, encoding="utf-8").read(), open(harness_py, encoding="utf-8").read()
    n_tests = len(re.findall(r"^    def test_\w+\(self\):", tests_src, re.M))
    n_removals = len(re.findall(r'^    \("', open(removals_py, encoding="utf-8").read(), re.M))
    T("safeguards: number of tests", rf"({n_tests} tests, which call neither the model nor \dfj{{}})")
    T("safeguards: number of removals", rf"A second script removes each of {n_removals} safeguards in turn from a copy of the code")
    C("safeguards: the refusals injected carry HTTP status 503, six in a row", "503 UNAVAILABLE" in tests_src and "max_retries:       int             = 6" in harness_src
      and "six consecutive refusals with HTTP status 503" in tex)
    lim = (re.search(r'return "".join\(diff\)\[:(\d+)\]', harness_src).group(1), re.search(r"max_chars:\s+int = (\d+)", harness_src).group(1),
           re.search(r'feedback.get\("test_output", ""\)\[:(\d+)\]', harness_src).group(1), re.search(r"test_results.output\[:(\d+)\]", harness_src).group(1))
    C("the two limits on the test output are the same", lim[2] == lim[3])
    T("limits of the prompts", rf"the failing-test source at {th(lim[1])} characters, a unified diff at {th(lim[0])}, the compile or test output at {th(lim[2])}, and the lists of failing tests and of regressions at eight entries each")
    C("... 'eight entries each'", "still_failing_targets[:8]" in harness_src and "regressions[:8]" in harness_src and "non_trigger_failing[:8]" in harness_src)
    T("limits of the Judge prompt", rf"the unified diff (its first {th(lim[0])} characters) and the structured test result (status, failing tests, and the first {th(lim[3])} characters of output)")
else:
    print("note: tests/ and src/ not found next to the checker; the counts of the failure-injection tests and the limits of the prompts were not checked")

# ── the abstract stays within the journal's limit ─────────────────────────
abstract = re.search(r"\\abstract\{(.*?)\}\n\n\\keywords", tex, re.S).group(1)
C("abstract: at most 250 words", len(re.sub(r"\\[a-zA-Z]+\{\}", "X", abstract).replace("~", " ").split()) <= 250)

print(f"{ok} checks passed, {bad} failed")
sys.exit(1 if bad else 0)
