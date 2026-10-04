# Worldview Agents — Research Experiment Design

Oct 4, 2026 · Patrick Buell

## Research question and hypotheses

Does framing an LLM agent with a worldview derived purely from foundational texts change how it performs tasks, interacts with other agents, and holds or shifts that worldview over time?

**H0 (null):** Worldview framing has no effect on task accuracy or completion rate.

**H1 (behavioral):** Worldview framing changes behavior on non-accuracy dimensions: risk tolerance, refusal rate, handling of ambiguity and deception, treatment of other agents, and tone.

**H2 (model interaction):** The size and direction of the effect differs by model vendor (Anthropic, OpenAI, xAI, open-weight), because each lab's default alignment interacts differently with the imposed worldview.

**H3 (contagion):** In multi-agent settings, agents proselytize, drift, or hold firm as a function of worldview, population ratio, and exposure duration. Drift is not symmetric: some worldviews dominate.

**H4 (lab default is not neutral):** The unprompted model is not secular in a neutral sense; it carries its lab's trained values. A defined secular control (Humanist Manifesto, UDHR) will behave measurably differently from the lab default.

## Worldview taxonomy

Every condition is a system prompt built only from a named foundational text, so each worldview is citable and reproducible. Tier 1 is scripture-only purist; tier 2 adds a sect's defining documents; tier 3 adds a specific theological or philosophical tradition.

| Family | Tier 1: scripture only | Tier 2: sect | Tier 3: tradition |
| --- | --- | --- | --- |
| Christianity | Bible (OT + NT) | Catholic (Catechism, Vatican II); Protestant (95 Theses, Westminster Confession); Orthodox (Nicene Creed, Seven Councils) | Aquinas (Summa); Calvin (Institutes); Augustine |
| Islam | Quran | Sunni (Hadith, Bukhari); Shia (Nahj al-Balagha) | Sufi (Rumi, Al-Ghazali) |
| Judaism | Torah / Tanakh | Rabbinic (Talmud); Orthodox vs Reform platforms | Maimonides (Guide for the Perplexed) |
| Hinduism | Vedas, Upanishads, Bhagavad Gita | Vaishnava; Shaiva; Advaita Vedanta | Shankara; Ramanuja |
| Buddhism | Pali Canon | Theravada; Mahayana (Lotus Sutra); Zen | Nagarjuna; Dogen |
| Sikhism | Guru Granth Sahib | — | — |
| Confucianism / Taoism | Analects; Tao Te Ching | Neo-Confucian (Zhu Xi) | — |
| Non-religious | Humanist Manifesto III; UDHR (secular control) | Stoicism (Meditations, Epictetus); Atheism (Russell, Dawkins); Nihilism (Nietzsche); Utilitarianism (Mill); Objectivism (Rand) | — |
| Lab default | No worldview prompt (control) | — | — |

Two rules keep this a purist design. First, prompts quote or paraphrase the text itself, never a description of how adherents behave today. Second, every tier-2 and tier-3 prompt is the tier-1 prompt plus the named addition, so the delta is isolated.

## Experimental design

Four factors, two experiment types. Experiment A (solo) tests H0, H1, H2 and H4 on a task ladder. Experiment B (multi-agent) tests H3 with population ratio and duration.

| Factor | Levels | Used in |
| --- | --- | --- |
| Worldview | Taxonomy above; pilot uses 6 | A, B |
| Model vendor | Claude, GPT, Grok, Llama/Qwen (open-weight) | A, B |
| Task tier | Basic, medium, high complexity | A |
| Population ratio | Majority (4:1), even (1:1), lone dissenter (1:4) | B |
| Exposure duration | Single session, 1 day, 1 week; each run two ways: wall-clock (scheduled wakes, persistent memory) and simulated (same turn count in one session) | B |

**Task ladder (Experiment A).** Each tier has at least 20 tasks, seeded and reused across every condition.

1. Basic: factual QA, summarization, arithmetic, simple code. Tests whether worldview degrades competence.
2. Medium: multi-step planning, negotiation with a scripted counterparty, resource allocation under scarcity, writing persuasive copy.
3. High: moral dilemmas (trolley variants, triage, whistleblowing), tasks with a hidden deception opportunity, tasks where the instruction conflicts with the worldview, long-horizon agentic tasks with tool use.

**Multi-agent protocol (Experiment B).** Agents share a workspace and a joint task, with a free-discussion channel. Each agent's worldview is re-probed at fixed checkpoints using a hidden questionnaire it does not see as a test. Runs go in both directions for each worldview pair. Duration is run both wall-clock and simulated with matched turn counts, so any difference isolates elapsed time and memory consolidation from sheer volume of exposure. Pilot uses simulated; the full grid adds wall-clock.

**Controls.** Every run is repeated with 5 seeds at temperature 0.7 and once at temperature 0. Prompt length and reading level are matched across worldviews so the effect is content, not verbosity. Order of tasks is randomized.

**Pilot grid.** 6 worldviews × 4 models × 3 task tiers × 5 seeds = 360 solo runs. Multi-agent pilot: 3 worldview pairs × 3 ratios × 2 durations × 2 models = 36 runs.

## Technical harness

Build it as a Python monorepo with Claude Code, with one adapter per vendor behind a common interface, so a run is just a config file.

| Layer | Choice | Why |
| --- | --- | --- |
| Model access | LiteLLM or OpenRouter as the unified gateway; vLLM or Ollama for open-weight on the Entrepreneur OS rig | One client, every vendor; local models cost nothing per token |
| Agent framework | Thin custom loop (system prompt + tools + memory), or Inspect AI from UK AISI | Inspect already has task/solver/scorer abstractions and multi-model support |
| Orchestration | Config-driven runner (Hydra or plain YAML); each run = worldview × model × task × seed | Reproducible, resumable, parallelizable |
| Multi-agent | LangGraph or a custom message bus; agents talk through a shared channel the harness logs | Need full control of turn order and what each agent sees |
| Logging | Every prompt, completion, tool call, token count, latency, and cost to JSONL; Langfuse or Weights & Biases for dashboards | Raw transcripts are the dataset |
| Storage | Postgres for run metadata and scores; S3 or local object store for transcripts; DuckDB or Snowflake for analysis | Query across 400+ runs without reloading files |
| Scoring | Rubric-based LLM judge (a model not under test) plus deterministic checks where possible; 10% hand-graded for judge calibration | Judge bias is a known confound; measure it |
| Versioning | Git for code and prompts; DVC or a prompts table with content hashes | A worldview prompt edit must invalidate old runs |

**Run lifecycle.** Config → render worldview prompt → spawn agent(s) → execute task → capture transcript → score → write to Postgres → aggregate. Experiment B adds a scheduler that wakes agents at intervals over a day or week, with persistent memory between wakes.

**Cost ceiling.** At roughly 5,000 tokens per solo run, 360 pilot runs across paid vendors is under $100. The week-long multi-agent runs are the expensive part; budget $300 to $500 for the pilot.

## Metrics and measurement

Every run produces one row of scores. Competence metrics test H0; behavioral metrics test H1 and H2; drift metrics test H3.

| Metric | How it is scored | Hypothesis |
| --- | --- | --- |
| Task accuracy | Deterministic check or rubric judge, 0 to 1 | H0 |
| Completion rate | Did the agent finish without abandoning or refusing | H0 |
| Refusal rate | Count of declined tasks or sub-steps, with the stated reason | H1 |
| Risk tolerance | Choices on gamble-style tasks, scored on expected-value deviation | H1 |
| Deception uptake | Did the agent take the hidden lying or cheating opportunity | H1 |
| Cooperation index | Resources shared, concessions made, in negotiation and allocation tasks | H1 |
| Moral choice profile | Vector of answers on dilemma tasks, compared to lab default | H1, H2 |
| Proselytizing rate | Unprompted references to the worldview per 1,000 tokens in multi-agent chat | H3 |
| Worldview drift | Cosine distance between checkpoint questionnaire answers and the agent's own baseline | H3 |
| Dominance | Which worldview the group's final joint decisions align with | H3 |
| Judge agreement | Cohen's kappa between LLM judge and hand grades on the 10% sample | Validity |

**Analysis.** Mixed-effects regression with worldview, model, and their interaction as fixed effects, seed as random effect. Effect sizes reported as Cohen's d against lab default. Pre-register the analysis plan on OSF before running the full grid so the result is credible.

**Qualitative layer.** Tag transcripts for recurring patterns (scripture citation, hedging, moral reasoning style). The best findings will likely be the surprising transcripts, not only the numbers.

## Outputs and distribution

Three artifacts, released together, each aimed at a different audience. The paper earns credibility, the repo earns adoption, and the talk earns reach.

| Output | Audience | Form | Channel |
| --- | --- | --- | --- |
| arXiv preprint | AI researchers, alignment community | 10 to 15 page paper, cs.AI and cs.CL, pre-registered on OSF | arXiv, then submit to a workshop (NeurIPS SoLaR, ICLR, or FAccT) |
| Open repo and dataset | Builders, replicators | GitHub: harness code, worldview prompts, task ladder, all transcripts, scores; HuggingFace dataset mirror | GitHub, HuggingFace, Papers with Code |
| Interactive explorer | Curious public, journalists | Web page to pick a worldview and a model and read real transcripts side by side | Own domain, linked from everything |
| Essay or blog post | Tech and general readers | 2,000 words, led by the three most surprising transcripts | Substack, Hacker News, LinkedIn, X |
| Talk | Conference and TED-style audiences | 15 minutes, built around one live demo of two agents disagreeing | AI Engineer Summit, local meetups, record for YouTube |

**Framing that travels.** The hook is not "religion in AI"; it is "what you tell an agent to believe changes what it does, and the labs' defaults are beliefs too." Lead with the contagion result if it holds; a chart of worldview drift over a week is the image people will share.

**Sequence.** Repo and preprint go up the same day. Blog post and explorer follow within a week while the preprint is fresh. Pitch the talk once there is a citable paper.

**Risk.** Religious framing invites misreading. State plainly in every artifact that prompts are built from texts, not from claims about believers, and publish the prompts so anyone can check.

## Phase 1 pilot and open questions

Start with 6 worldviews on 4 models, solo tasks only, to find out whether the effect exists before investing in the week-long multi-agent runs.

**Pilot worldviews:** Bible purist, Quran purist, Torah purist, Pali Canon purist, secular humanist control, lab default.

- [ ] Write and length-match the 6 worldview prompts
- [ ] Build the task ladder: 20 tasks per tier, with answer keys or rubrics
- [ ] Stand up the harness: gateway, runner, JSONL logging, Postgres
- [ ] Run 360 solo pilot runs; hand-grade 36 for judge calibration
- [ ] Pre-register the full-grid analysis plan on OSF
- [ ] Decide go or no-go on Experiment B from pilot effect sizes

**Open questions**

- Who writes the worldview prompts, and how do we check them for fidelity to the texts? A reviewer per tradition would strengthen the paper.
- Should the LLM judge be blind to the worldview condition? Likely yes; it changes the scoring pipeline.
- For week-long runs, what does "time" mean to an agent: wall-clock wakes, or simulated days of accumulated context?
- Which open-weight models, and do they run on the Entrepreneur OS rig or in the cloud?
- Is there an IRB or ethics-review step worth doing voluntarily, given the subject matter?

## Claude Code kickoff prompt

Copy this into Claude Code in an empty folder that contains this doc exported as `DESIGN.md`.

```markdown
Read DESIGN.md in full before doing anything. It is the research design for a multi-model agent experiment; treat it as the spec.

Scaffold a Python 3.11 monorepo named `worldview-agents` using uv. Scope this first PR to three things only: the model gateway, the run orchestrator, and logging. Do not build the task ladder, the judge, the multi-agent bus, or any analysis yet.

Gateway: a single `complete(model, messages, tools=None, seed=None, temperature=0.7)` function behind LiteLLM, with adapters configured for Anthropic, OpenAI, xAI, and an OpenAI-compatible local endpoint (vLLM/Ollama). Read API keys from `.env`. Return a dataclass with text, tool calls, token counts, latency, and estimated cost.

Orchestrator: a YAML-driven runner. A run config names a worldview prompt file, a model id, a task id, a seed, and a temperature. Worldview prompts live in `prompts/worldviews/*.md` with a YAML front-matter block for name, tier, family, and source texts. Add six placeholder files matching the Phase 1 pilot list in DESIGN.md. The runner expands a grid config into individual runs, executes them with configurable concurrency, and is resumable: skip runs whose output already exists.

Logging: every run writes one JSONL line per model call to `runs/<run_id>/transcript.jsonl` and a `meta.json` with the full resolved config, content hashes of the prompt and task files, git commit, timestamps, and totals. Also write a row to a SQLite table `runs` (we will move to Postgres later; keep the schema in `db/schema.sql`).

Add a `tasks/` folder with one trivial stub task so the end-to-end path can be smoke-tested, and a `make smoke` target that runs it against one cheap model.

Constraints: no framework beyond LiteLLM and pydantic for this PR. Type hints everywhere. Tests with pytest for the grid expansion, resumability, and hash invalidation. Write a `HANDOFF.md` at the end describing what exists, how to run the smoke test, and what the next PR should build.

Before writing code, give me a short plan with the file tree and ask any clarifying questions.
```
