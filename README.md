# ChildGuard-Bench

**STATUS: EXPLORATORY.** All results in this repository are exploratory, not confirmed. A human check of the AI judges found low agreement (Cohen's kappa 0.10, below the preregistered bar of 0.70), so under the preregistration the primary results are reported as exploratory. Please read the limitations below before using any number.

ChildGuard-Bench tests whether AI chatbots answer differently when the same request comes from an implied child instead of an implied adult. It is an independent, preregistered study by John Jeon (New York University). It is not a journal paper and has not been peer reviewed.

## What was tested

- **Items:** 480 synthetic prompts in 100 families (400 protective, 80 benign), in four clusters: physical risk (PHYS), parasocial attachment (PARA), parental evasion (EVAS) and credulity (CRED). Each protective item comes as three prompts: a neutral formal adult version, an adult version in the same casual style as the child version, and a child version that implies age through cues (no prompt states an age). The comparison of interest is child versus style-matched adult.
- **Models:** gpt-6.1-sol and gpt-6-luna (OpenAI), claude-sonnet-5-5 (Anthropic), gemini-3.8-flash (Google), each pinned to an exact model ID and called through the developer's own API in October 2026. Every query was a fresh single-turn conversation with no system prompt and the provider's default safety settings, with a 4,096-token output limit that includes hidden reasoning.
- **Runs:** a first run (temperature 0 where the provider allows it, one response per prompt, the basis for the primary tests) and a second run (temperature 0.7, top-p 0.95, three draws). Some models accept only default sampling, so for those both runs use default sampling.
- **Judging:** two AI judges (claude-haiku-5-5 and gemini-3.8-flash) scored every response; a third judge broke ties.
- **Registration:** the plan was registered on OSF before the full run. OSF link: [ADD LINK AFTER THE PROJECT IS MADE PUBLIC].

## Main results (first run, exploratory)

Rates are for style-matched adult prompts compared with child prompts, from `results/results_t0.csv`. Holm-adjusted p-values are from the preregistered item-level paired t-tests.

| Question | Style-matched adult | Child | Difference (child minus adult) | Holm p |
| --- | --- | --- | --- | --- |
| Physical risk: violation rate | 14.0% | 6.5% | −7.5 points | 0.024 |
| Parasocial attachment: violation rate | 9.7% | 6.4% | −3.3 points | 0.445 |
| Parental evasion: help given with the evasion request | 78.5% | 34.5% | −44.0 points | below 0.001 |
| Credulity: violation rate | 3.5% | 5.3% | +1.8 points | 0.445 |

How to read this: models gave far less help with evading parental controls when the prompt implied a child, as predicted. The physical-risk difference runs against the prediction, because child prompts had fewer violations than casual adult prompts. The other two differences are small and not statistically significant. Whether these differences are real depends on how far the AI judge labels can be trusted, which the audit did not establish. A confirmed claim would need clarified judge instructions, a new registration and new data.

## Limitations

- **Judge audit failed the registered bar.** The author scored 100 first-run responses by hand, blind to model and judge labels. Cohen's kappa for strict violation was 0.10. On the first sheet, which came back with one row blank, agreement was 78.8% on 99 rows (95% interval −0.12 to 0.34). On a second copy saved minutes later with that row filled in, agreement was 79.0% on 100 rows (95% interval −0.11 to 0.34). Both versions are reported. The author scored alone, wrote the grading specifications with AI assistance, and partly judged the grading rules instead of the responses. No second audit was run.
- **Items were AI-generated, and one generator is also a tested model.** The items were generated with claude-sonnet-5-5, which is also an evaluated model. Child prompts are more fluent than real children's writing and share wording with adult prompts by design.
- **Judge overlap and substitution.** The judges come from the same developers as three of the four evaluated models, so a judge may score its own family's responses more leniently. After OpenAI deactivated the author's API account on Oct 19, 597 tie-break judgments used claude-opus-5-5 instead of the registered gpt-6-luna.
- **Scope.** The study is US-normed, single-turn only, and describes the pinned model versions on the logged access dates. The models are closed and cannot be re-run if a provider changes or retires them.
- **Sampling.** Three of the four models cannot be run at the planned temperatures, so their results describe default sampling.

Every departure from the registration, and every event handled as registered, is in the Deviations Log (`docs/deviations_log.md`).

## What is in this repository

| Path | Contents |
| --- | --- |
| `data/childguard_bench_items_v1.6_DRAFT.csv` | The frozen item set: 480 rows with prompts, cue markers and ideal/violation specifications. SHA-256 `247a38de9e037e212cb819104ef7de5f85a5094db908ca9c0a4f03d720de666a` (see `data/FROZEN_MANIFEST.txt`). |
| `results/` | Aggregate results tables, pooled across all four models: the registered tests for the first and second runs, the lenient-threshold robustness check and the sensitivity analyses. |
| `code/` | The collection and judging pipeline, the Colab notebooks, the judge prompt, the analysis code and tests, the audit scripts, and the dataset setup scripts. |
| `docs/` | The technical report, the Deviations Log and a short overview. |

To check the dataset, compute the SHA-256 of `data/childguard_bench_items_v1.6_DRAFT.csv` and compare it with the value above. Do not open and re-save the file in a spreadsheet program, which changes the bytes.

## What is not included

- **Full model responses and judge rationales.** They can contain working methods for bypassing parental controls and other sensitive content, so they are not published. The preregistration commits to releasing prompts, labels, sanitized excerpts and statistics only.
- **Item-level labels and per-model results.** The item-level labels and the per-model exploratory tests (McNemar) are added on or after Nov 28, 2026. The preregistration requires each model provider to receive its own item-level results at least 30 days before item-level findings are published. Anthropic was sent its results on Oct 28, 2026. OpenAI and Google could not be reached; see the Deviations Log.
- **The raw audit sheet.** It is kept private.

## Running the code

The scripts were written in the author's environment and contain some hard-coded paths (for example in `code/analysis/sensitivity.py`), which you will need to adjust. API keys are read from environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`); in Colab they come from Colab Secrets. No keys are stored in this repository. Re-running the collection requires your own API access and will produce different responses, since the models and their versions change.

## Ethics

The prompts are synthetic. No human participants or personal data are involved. Prompts about distress at home refer to US resources (the Childhelp National Child Abuse Hotline and the National Domestic Violence Hotline) inside the specification text.

## License and contact

License: [TO BE CHOSEN BY THE AUTHOR BEFORE RELEASE].

Questions, corrections and notes about how your model was handled are welcome. Open an issue, or contact John Jeon at jj4456@nyu.edu.
