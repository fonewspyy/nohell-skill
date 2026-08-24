# engineering-skills — skills that force an agent to think like a senior before it types

[![validate](https://github.com/fonewspyy/nohell-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/fonewspyy/nohell-skill/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **The skills are written in Thai.** This page explains what the repo is and how to install it; the skills themselves are Thai-language instructions the agent reads and follows. Claude handles Thai natively, so they work no matter what language you talk to it in — but reading or editing the rules yourself needs Thai. [CONTRIBUTING.md](CONTRIBUTING.md) explains why they aren't translated.

The problem isn't that agents can't write code. The problem is that agents **start writing too early**, and accumulate debt faster than a human ever could. So this isn't another pile of rules — it's an enforced order of thinking.

```
skills/
├── principal-engineer/   ← always enter here: Impact Map, Ask Gate, router
├── kickoff/              ← starting something new: the agent drives, phase by phase
├── nohell/               ← 447-entry anti-pattern catalog + machine-checkable rules + a DB scanner
│   └── commands/nohell-dig.md   ← mine repo history for the hells that actually hurt
├── business-rules/       ← rule ownership, effective dates, read/write symmetry, workflow, money
├── archaeology/          ← evidence levels, caller inventory, finding rule copies by shape
└── conventions/          ← naming, business vocabulary, the standard SP skeleton
    └── templates/        ← copy-paste-ready SP templates (typed parameters, and JSON payload)

docs/
├── llm-reality.md        ← 60 pairs of belief vs. reality about LLMs and agents
└── tooling-2026.md       ← tools that actually pay off for a one-person team, and when to switch
```

## The pipeline

```
work arrives
   ↓
principal-engineer  → 13-field Impact Map + Ask Gate    ← a blank field means: don't write code yet
   ↓
router picks the lenses this kind of work needs
   ↓
ponytail (external)  → does this need to be written at all?
   ↓
nohell's 12 core rules → will writing it this way become hell?
   ↓
specialist lenses    → business-rules / archaeology / a HELL-CATALOG category
   ↓
close the task using the same Impact Map as a checklist
```

## What each one answers

| skill | the question it answers | when it loads |
|---|---|---|
| principal-engineer | what will this touch, and what do I still not know | every task, always loaded |
| nohell (SKILL.md) | will writing it this way become hell | every task, always loaded (~3–4k tokens) |
| nohell (HELL-CATALOG) | which specific hells live in this domain | only the categories the work touches, during review/audit |
| business-rules | who owns this rule, and as of which date | anything touching money, stock, permissions, status, history |
| archaeology | how does the system *actually* behave right now | before touching old code, before consolidating, whenever unsure |
| kickoff | how do we start, and what haven't I asked yet | new projects, or a large feature starting from nothing |
| conventions | what should this new thing be called, and what shape | every time you create an SP, table, file, function, or endpoint |

## Install

**Always install from a tag; never track `main`.** Rules change between releases — if your agent reads
`main`, its behaviour shifts mid-sprint with no record of why. See [CHANGELOG.md](CHANGELOG.md).

```sh
git clone --branch v0.11.0 --depth 1 https://github.com/fonewspyy/nohell-skill.git
cp -r nohell-skill/skills/* ~/.claude/skills/          # available in every project
# or scoped to one project
cp -r nohell-skill/skills/* .claude/skills/
```

Then point your project's `AGENTS.md` / `CLAUDE.md` at `skills/principal-engineer/SKILL.md` as the first gate.

The `/nohell-dig` command installs separately — Claude Code reads slash commands from `commands/`, not from `skills/`:

```sh
cp nohell-skill/skills/nohell/commands/nohell-dig.md ~/.claude/commands/
```

The rule runner lives at `scripts/nohell-check.py`, **not** under `skills/`, so the copy above
does not deliver it. Keep the clone and call it from there, or copy just that file anywhere —
it locates `hell-rules.yaml` on its own, including at `~/.claude/skills/nohell/`.

```sh
cd /path/to/repo-under-test
python /path/to/nohell-skill/scripts/nohell-check.py        # diff-only
```

These belong in the **target repo**, not here:

- `CONSOLIDATIONS.yaml` (from `skills/nohell/CONSOLIDATIONS.example.yaml`) — the register of open consolidation cycles
- `docs/impact/` — one Impact Map per task
- `docs/adr/` — decisions that are expensive to reverse
- `docs/archaeology/` — investigation results

## The catalog

447 entries across 28 categories. Every entry is one row:
`ID | priority | the hell | what you'll see in the wild | the enforceable rule that replaces it`.

`ARCH` `SQL` `DATA` `TXN` `API` `CODE` `CACHE` `ERR` `OBS` `SEC` `CFG` `SHIP` `TEST` `PERF` `INT` `JOB` `TIME` `FILE` `SSOT` `LEG` `TEAM` `AI` `FE` `TYPE` `AGG` `MEAS` `REG` `TOOL`

**P1** 136 — data silently written wrong, lost, or duplicated · a leak · money moving wrongly
**P2** 154 — loud breakage (crash, error, hang) that recovers without touching historical data
**P3** 157 — the cost of reading and maintaining

All 447 entries were re-rated against one written criterion (see [CONTRIBUTING.md](CONTRIBUTING.md)). **"Very severe" is not what makes something P1** — a full-day outage stays P2 if the data is correct once it recovers. P1 is for data that is already wrong and nobody was told.

67 of the entries are machine-checkable and carry a detection command in `skills/nohell/hell-rules.yaml`;
`skills/nohell/detect-sqlserver.sql` scans a live SQL Server and maps what it finds back to catalog IDs.

## Consistency check

This repo forbids `SSOT-01` in other people's code, so it can't commit it in its own. Two tools split the work.

`validate-catalog.sh` checks the catalog **shape**: duplicate IDs · numbering gaps · missing priorities · malformed rows · **IDs referenced by a skill or doc that do not exist
in the catalog** · **patterns using lookaround without declaring `engine: pcre2`** · **token-size claims that
no longer match the file** · `ใช้กับ` values outside the allowed set · severities in `hell-rules.yaml` that
disagree with the catalog · **patterns that match across lines without declaring `multiline: true`**

`build-summary.py` owns **every declared number** — the catalog title count, the per-category heading counts,
the summary table, and the counts written into prose (entries · categories · P1/P2/P3 · machine-checkable
rules). Its `FACTS` table is the single place that says which number must equal what, and without `--check`
it **rewrites them correctly** rather than just complaining. A number a human has to maintain is a number
that will drift.

```sh
sh scripts/validate-catalog.sh
python scripts/build-summary.py --check   # does the summary table still match reality?
```

CI runs both on every push. The summary table at the end of `HELL-CATALOG.md` is generated, not hand-maintained — it had silently lost an entire 18-entry category before that was enforced.

## Running the automated layer — `nohell-check`

The primary mode is **diff-only**: it reads only the *added* lines from `git diff` and runs the
rules against those. A hit on an added line is new by definition, so diff-only **is** the
`ratchet` (don't add more, not don't have any). You do not have to clear old hits before turning
the gate on — needing to is why absolute-mode gates always get switched off.

```sh
pip install pyyaml                                  # required, not stdlib
python scripts/nohell-check.py                      # diff against origin/main
python scripts/nohell-check.py --base HEAD~1
python scripts/nohell-check.py --full               # whole repo (git-tracked files)
python scripts/nohell-check.py --full --baseline    # write .nohell-baseline.json
```

Exit codes are a contract: `0` clean · `1` a `gate.block_on` rule hit an added line ·
**`2` could not run** (no `rg`, no PCRE2, pattern failed to compile). Never swallow `2` as `0` —
a gate that goes silent and passes everything is worse than no gate at all.

| It runs | It does **not** run (reported every time, never hidden) |
|---|---|
| 40 `kind: regex` rules with the flags each declares (`engine: pcre2` → `-P`, `multiline: true` → `-U`) | 13 `kind: cmd` — they shell out to eslint / gitleaks / pnpm audit; running commands from a config file is an arbitrary-execution hole |
| per-rule `allow_comment` and `exclude` | 12 `kind: sql` — needs a live database; run `detect-sqlserver.sql` yourself |
| repo-level `.nohellignore` | 2 `kind: manual-checklist` — a human has to read these |

`.nohellignore` exists for exactly one case: **a file that defines the rules will match its own
rules.** Do not use it to dodge work — to exempt a single line, use that rule's `allow_comment`.

Runner tests live in `scripts/test-nohell-check.sh` (10 known-answer diff cases, both directions).

## Known limitations — read before wiring this into CI

Field-tested against a real enterprise repo (389 SQL Server files + .NET + TypeScript). What that found:

**1. Six rules require PCRE2.** `SQL-16`, `SQL-30`, `ERR-11`, `CFG-03`, `SHIP-05`, `FE-07` use lookaround.
Rust regex (plain `rg`) and `grep -E` **reject them outright**. If your runner swallows that error, the gate goes
silent and passes everything — worse than having no gate. Run them with `rg -P`; they declare `engine: pcre2`
and the validator enforces that they keep doing so.

**1b. Two more rules require multiline.** `SQL-26` and `ERR-09` match across lines (they contain a `\n`
that has to match), so they need `rg -U`. Same silent failure if you omit it — measured: `SQL-26` reports
**0** under plain `rg` but **11 hits across 7 files** with `-U`. Both declare `multiline: true` and
validator check 13 enforces it. Note `[^\n]` alone does **not** need `-U` — it excludes newlines
rather than matching them.

**2. `gate.mode` defaults to `ratchet`, not `absolute`.** 136 of 447 entries are P1. Turning on absolute mode
against an existing codebase produces thousands of P1 hits on day one (measured: `NOLOCK` alone, 6,355 hits
across 219 of 389 files). That is a backlog, not a gate, and it gets switched off. `ratchet` enforces
**don't add more**, not **don't have any**.

**0. Every entry declares the stack it applies to.** The `ใช้กับ` column: 358 entries (80%) are
stack-independent, the rest are tagged `RDBMS` (49), `SQL Server` (13), `มี SP` / stored-procedure shops (7),
`เว็บ` / web (17), `TS/JS` (2), `.NET` (1). Added after testing against a MySQL codebase where 17 of the 31
`SQL` entries did not apply at all and nothing in the file said so. Filter before you read — a Python +
PostgreSQL shop reads 407 of 447 and skips the other 40.

**3. The automated layer is triage, not a gate.** Measured on a real codebase (MySQL + TS, 1,413 files):
P1 rules pointed at 473 of 1,413 files (33%), which contained 16 of the 18 files with real bugs —
**a lift of only 2.66x over random**. It caught **0 of the 21 verified bugs**, because every one of them was
semantic. What actually works is the **catalog as a lens a person or agent reads**: 71% recall
(86% counting partial matches). Use the regex layer to decide which files to read first, not to block.

**3b. Regex is the first pass, not the verdict.** Several rules over-match deliberately (`SQL-31` flags every
`@iJson nvarchar(max)`), per the philosophy stated at the top of the rules file: a false positive is cheaper
than a false negative. Output is meant to be read by a person or an agent, not blocked on directly.

**4. Recall against real bugs is ~42%.** Tested against 19 production bugs recorded in a real repo: 8 caught
directly, 12 if partial matches count. The hits cluster in the money/SSOT categories — the surfaces that bleed
most often. The misses cluster into named gaps with no category yet (measurement tools configured unlike prod ·
aggregates over mixed-kind row sets · numeric type inference · two-layer registries drifting apart).
See [CONTRIBUTING.md](CONTRIBUTING.md).

## External skills used alongside

| skill | role | overlap with this repo |
|---|---|---|
| ponytail | reduces what the agent *builds* | none — ponytail governs volume, nohell governs shape |
| caveman | reduces what the agent *says* | none at all, different half of the problem |
| impeccable | UI work | pairs with the `FE` category in the catalog |

## Why there are no separate frontend/ backend/ database/ security/ folders

Because that would be **`SSOT-01` committed against ourselves**: creating C (a new skill) without deleting A (the existing catalog category), until the SQL rules live in two places and drift apart.

The catalog is already split by domain across 28 categories. What was missing was *knowing which category this task needs* — and that's the router in `principal-engineer`, not another folder.

A new skill is only justified when it carries a **process** the catalog can't express. `business-rules`, `archaeology`, `kickoff`, and `conventions` clear that bar. "frontend" doesn't — it's a list of things not to do, which is exactly what the catalog is for.

## Not yet covered

No categories yet for **MOBILE** (offline/sync/barcode scanners/duplicate submits over flaky warehouse wifi), **AI-ML** (datasets, leakage, preprocessing parity, thresholds, drift), **INFRA** (containers, reverse proxies, TLS, backup/DR), or **NET** (connection pools, keep-alive, proxy timeouts, backpressure — currently scattered across `ERR`/`PERF`).

These belong as new categories in the existing catalog, not as new skills. Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
