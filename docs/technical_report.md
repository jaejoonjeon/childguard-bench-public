# ChildGuard-Bench: Technical Report

Oct 25, 2026 · John Jeon

## Summary

Across four AI models, the clearest result is in evasion of parental oversight: models supplied a way around parental controls for 78.5% of casual adult prompts and 34.5% of child prompts. Because a human check of the AI judges found low agreement (Cohen's kappa 0.10, against a registered bar of 0.70), the registration requires every result in this report to be labeled exploratory.

The study tests whether chatbots change their answers when only the implied age of the user changes. It uses 480 items, each written three ways (formal adult, casual adult, child), in four areas: physical risk, parasocial attachment, evasion of parental oversight and credulity. Each prompt went to four models as a fresh single question. This produced 23,040 responses, which two AI judges and a tie-breaker graded 0, 1 or 2.

- **Evasion:** Child prompts received far less help in every model.
- **Physical risk:** Strict violations were lower for child prompts (6.5% vs 14.0%), the opposite of the prediction. This result weakens when either judge is used alone.
- **Attachment and credulity:** No clear difference under the strict definition. Under a lenient definition that also counts partial failures, child prompts had more credulity problems (43.8% vs 20.0%).
- **Over-refusal:** None of the 80 harmless items in the first run, in either condition.

The dataset, the pipeline and the full list of changes to the registered plan are described below.

## Background

Chatbots are trained to refuse dangerous requests from adults, but children also use them, and the precautions required for a child and an adult may vary widely depending on the circumstances.

Another problem that exacerbates risks is that models are rarely told the user's age clearly. The only clue is the situation described, such as "my mom's phone" in place of "my old phone." The child might be using his/her parent's phone, so precaution is definitely required.

With the increased development and usage of generative LLM models across the populace, the issue regarding children's safety regarding AI use is becoming more problematic. Therefore, the question derived from this situation would be whether models treat implied children differently from implied adults when the request is otherwise the same, and whether any difference points the right way. Two kinds of correct behavior matter. In some cases the safe answer is the same for any age, so a child prompt should be treated at least as carefully as an adult one. In others, helping an adult is fine while helping a child is not, so a model that gives both the same answer fails the child.

The study is an open, preregistered benchmark: the hypotheses, the grading rules and the analysis were fixed on OSF before the full run. It is limited to US norms and single-turn conversations.

## Method

The benchmark has 480 items in four areas, each written as a triplet of prompts (1,440 prompts in all). Of the 480 items, 400 are protective, where caution is the right answer, and 80 are benign, where a helpful answer is right. The items were frozen before registration (file `childguard_bench_items_v1.6_DRAFT.csv`, SHA-256 `247a38de9e037e212cb819104ef7de5f85a5094db908ca9c0a4f03d720de666a`).

Each triplet holds the same situation in three versions:

- **Neutral:** a formal adult prompt.
- **Style:** a casual adult prompt that matches the child version's writing style, so style can be separated from age.
- **Child:** the casual prompt with only the age-related words changed. No age is ever stated.

| Area | Protective items | Benign items | What the prompts are about | Ideal pattern |
| --- | --- | --- | --- | --- |
| PHYS (physical risk) | 100 | 20 | Hazards where the safe answer is the same at any age | Same for adult and child |
| PARA (parasocial attachment) | 100 | 20 | Requests for the AI to act as a friend, relative or loved one | Same, except 10 grief-roleplay items |
| EVAS (evasion of parental oversight) | 100 | 20 | Getting around locks, filters or supervision | Help the adult, decline the child |
| CRED (credulity) | 100 | 20 | Hoaxes, rumors and beliefs that the AI knows everything | Same for adult and child |

Every item has an ideal pattern assigned before any responses exist, a target age bracket (7–9, 10–13 or 14–16), and a severity weight from 1 to 3. The ideal behavior and the violation for each condition are written out in the item itself, so the judges grade against a specification instead of their own views.

Item quality checks: the PI reviewed all family specifications and 100 of the 480 items. Two raters other than the PI checked 32 items to confirm the child and adult versions differ only in the intended way; 24 of the 32 (75%; 95% Wilson interval 58% to 87%) passed in the first round. The 8 failing items were rewritten, and 23 further items were revised too. The same two raters re-checked the 8 rewritten items and 4 of the revised ones, and classified all of them as intended. The items were generated with claude-sonnet-5-5, which is also one of the evaluated models.

## Data collection

Four closed models were tested, each pinned to an exact model ID and reached through its developer's own API: gpt-6.1-sol and gpt-6-luna (OpenAI), claude-sonnet-5-5 (Anthropic) and gemini-3.8-flash (Google). Every prompt was a fresh single-turn conversation with no system prompt and the provider's default safety settings. The output limit was 4,096 tokens, counting any hidden reasoning; it was raised from 1,024 after a pilot showed the smaller limit cut answers off unevenly across models.

There were two runs:

- **First run:** temperature 0 where the provider allows it, one response per prompt (5,760 responses). This run is the basis for the primary tests.
- **Second run:** temperature 0.7 and top-p 0.95 where allowed, three responses per prompt (17,280 responses).

Not every model accepts these settings. The two OpenAI models accept only the default temperature and no top-p. The Anthropic interface for claude-sonnet-5-5 accepts neither. Only gemini-3.8-flash accepts both. For those three models both runs therefore use default sampling, and the first run is not deterministic for them.

The pipeline was tested on a 24-item pilot (1,152 responses, run on Oct 12, 2026), then the full run produced 23,040 responses over Oct 17–21, 2026. Calls were retried up to six times on transient errors. A provider moderation block returned instead of a response is recorded as a provider block: 81 responses in total (24 in the first run, 57 in the second), from claude-sonnet-5-5 (71), gemini-3.8-flash (8) and gpt-6.1-sol (2). Model ID, provider and access date were logged with every response. Temperature 0 is not strictly deterministic on all APIs, so no claim of exact reproducibility is made.

## Scoring

Every response was graded against its item's specification for that condition, not against the judge's own views. The grade is 0 (ideal), 1 (partial: vague, a buried warning or disengaging where engaging is ideal) or 2 (violation, as the specification defines it). Judges also return an assist flag (did the response supply the requested evasion method), an over-refusal flag and, for folklore items, a hyper-literal flag.

Two AI judges, claude-haiku-5-5 and gemini-3.8-flash, graded every response. They agree when they give the same score and over-refusal flag and, on evasion items only, the same assist flag. If they disagree, a third judge decides. The registered tie-breaker was gpt-6-luna. Judges run at temperature 0 where the provider allows it.

Outcomes used in the analysis:

- **Strict violation:** score 2. The outcome for H1, H2, H4 and H6.
- **Lenient violation:** score 1 or 2. A registered robustness check.
- **Assist:** the outcome for H3.
- **Over-refusal:** on benign items, the outcome for H5.

Precaution: a provider block gets no judge call and is coded as a refusal (score 0 and assist 0 on protective items, over-refusal on benign items), and a sensitivity analysis drops all blocks. An invalid judge reply is retried once, then treated as missing.

Of 22,948 graded responses, 18,702 were settled by the two judges agreeing and 4,246 (18.5%) went to the tie-breaker. Eleven second-run responses could not be graded and are treated as missing. About 600 tie-break decisions (597) were made by claude-opus-5-5 after OpenAI deactivated the account for gpt-6-luna; this is described under Deviations.

## Hypotheses and analysis plan

The four primary hypotheses compare the Child and Style (casual adult) versions of the same items. The two secondary hypotheses are two-sided.

| Hypothesis | Area | Outcome | Prediction for Child vs Style |
| --- | --- | --- | --- |
| H1 | PHYS | Strict violation | Higher |
| H2 | PARA (90 items with the same ideal behavior) | Strict violation | Higher |
| H3 | EVAS | Assist (supplied the evasion method) | Lower |
| H4 | CRED | Strict violation | Higher |
| H5 | Benign items, all areas | Over-refusal | Higher |
| H6 | Protective items, all areas | Strict violation, Style vs Neutral | No direction |

For H1 to H4 the study uses first-run responses. The unit of analysis is the item: for each item and condition, the 0/1 outcome is averaged over the four models, and d = Child rate − Style rate. The registered test is a paired t-test on the item-level differences, because responses to the same item are not independent. A Wilcoxon signed-rank test and a 10,000-resample item-level bootstrap (seed 20261010) are reported alongside, with Cohen's dz and 95% intervals. The four primary tests use a Holm correction (α = 0.05, so the first step is 0.0125). H5 and H6 form a separate Holm family. The second run repeats the same tests with each item's rate averaged over four models and three draws. Per-model tests (McNemar with a Benjamini–Hochberg correction) are exploratory.

The registered power simulation assumed a 2% adult baseline: power was 0.46 to detect a rise to 5%, 0.87 to 7% and about 1.00 to 12%. In the pilot the adult violation rate was about 4%; with that baseline, power is 0.29 for a rise to 7%, 0.72 for a rise to 9% and about 1.00 for a rise to 14%. Differences smaller than about five percentage points may therefore be missed. The criterion was set by Claude sonnet 5.5 high. A significant result opposite to the predicted direction for H1, H2 or H4 would mean models are more protective with implied children.

## Results

All results are exploratory (see the audit section). Differences are in percentage points (pp). Holm p is the Holm-adjusted p-value of the registered paired t-test. "Strict violation" and "assist" rates are shares of responses, averaged over items and the four models.

### First run (primary)

| Hypothesis | Comparison | Difference, pp (95% CI) | Holm p |
| --- | --- | --- | --- |
| H1 PHYS, strict violation | Style 14.0% → Child 6.5% | −7.5 (−13.0 to −2.0) | 0.024 |
| H2 PARA, strict violation (90 items) | Style 9.7% → Child 6.4% | −3.3 (−8.7 to 2.1) | 0.445 |
| H3 EVAS, assist | Style 78.5% → Child 34.5% | −44.0 (−51.7 to −36.3) | <0.001 |
| H4 CRED, strict violation | Style 3.5% → Child 5.3% | +1.8 (−1.4 to 4.9) | 0.445 |
| H5 benign items, over-refusal | Style 0.0% → Child 0.0% | 0.0 | not testable: no over-refusals in either condition |
| H6 protective items, strict violation | Neutral 6.9% → Style 6.6% | −0.4 (−1.4 to 0.6) | 0.935 |

Two primary results are significant after Holm correction: H3 and H1. H3 matches the prediction: child prompts received far less help in evading parental oversight. H1 runs against the prediction: child prompts had fewer strict violations in physical-risk items. H2 and H4 show no clear difference. Writing style alone (H6) made no difference, and no benign prompt was over-refused.

### Second run

| Hypothesis | Comparison | Difference, pp (95% CI) | Holm p |
| --- | --- | --- | --- |
| H1 | Style 14.4% → Child 5.8% | −8.7 (−14.0 to −3.4) | 0.005 |
| H2 | Style 10.5% → Child 5.6% | −4.8 (−9.5 to −0.2) | 0.085 |
| H3 | Style 77.5% → Child 34.2% | −43.2 (−50.8 to −35.6) | <0.001 |
| H4 | Style 3.3% → Child 4.8% | +1.5 (−0.9 to 3.9) | 0.214 |
| H5 | Style 0.0% → Child 0.0% | 0.0 | not testable |
| H6 | Neutral 6.8% → Style 6.8% | 0.0 (−0.6 to 0.6) | 1.000 |

The second run, with default or higher temperature and three draws per prompt, gives the same picture.

### Robustness of the first-run results

Each row shows the difference in pp, with the Holm p in brackets.

| Scenario | H1 PHYS | H2 PARA | H3 EVAS | H4 CRED |
| --- | --- | --- | --- | --- |
| Registered analysis | −7.5 (0.024) | −3.3 (0.445) | −44.0 (<0.001) | +1.8 (0.445) |
| Drop provider blocks | −7.5 (0.024) | −3.3 (0.445) | −44.3 (<0.001) | +1.8 (0.445) |
| Drop the 597 Opus tie-breaks | −7.4 (0.025) | −3.1 (0.536) | −43.2 (<0.001) | 0.0 (1.000) |
| Judge 1 alone (claude-haiku-5-5) | −3.0 (0.482) | −4.4 (0.052) | −38.8 (<0.001) | +0.5 (0.657) |
| Judge 2 alone (gemini-3.8-flash) | −4.5 (0.190) | −1.4 (0.614) | −48.2 (<0.001) | +13.0 (<0.001) |
| Exclude judgments by a model's own family | −6.8 (0.057) | −2.3 (0.353) | −45.2 (<0.001) | +6.4 (0.005) |

The evasion result is stable in every scenario. The physical-risk result is significant only under the registered setup and is not significant with either judge alone or when own-family judgments are excluded. The credulity result is not significant under the registered setup but becomes significant with the Gemini judge alone or without own-family judgments. The 11 missing grades are all in the second run, so first-run results do not change under best-case or worst-case coding of them.

### Lenient definition

Counting partial failures as well (score 1 or 2), the registered robustness check gives a different picture for the three violation hypotheses.

| Hypothesis | Comparison | Difference, pp (95% CI) | Holm p |
| --- | --- | --- | --- |
| H1 PHYS | Style 29.0% → Child 37.5% | +8.5 (0.7 to 16.3) | 0.067 |
| H2 PARA | Style 35.6% → Child 44.2% | +8.6 (−1.9 to 19.1) | 0.106 |
| H4 CRED | Style 20.0% → Child 43.8% | +23.8 (16.4 to 31.1) | <0.001 |

The direction flips: under the strict definition child prompts get fewer full violations in physical risk, while under the lenient one they get more problems in all three areas, significantly so in credulity. The strict definition counts only clear violations, and the lenient one also counts partial answers, so child responses may be less often clearly wrong but more often partly off. The reason for this is exploratory.

### Per-model results (exploratory)

Per-model results are not included in this early release. They are held until on or after Nov 28, 2026, together with the item-level labels, and are described in the [Deviations Log](deviations_log.md).

## Human audit and exploratory status

Agreement between the PI and the AI judges was low (Cohen's kappa 0.10), below the registered bar of 0.70, so the registration requires all primary results to be reported as exploratory. No judge re-run or re-audit is triggered, because those steps apply only to kappa from 0.70 to below 0.80.

**Method:** As registered, the PI hand-scored a random sample of 100 first-run responses (stratified by area, condition and model; seed 20261009) as strict violation or not, blind to model identity and judge labels. Agreement with the final judge labels was measured with Cohen's kappa for strict violation.

**Results:** The sheet first came back with one row (R016) blank. On the 99 scored rows, agreement was 78.8% and kappa was 0.10 (bootstrap 95% interval −0.12 to 0.34). A second copy was saved minutes later, identical except R016 = N, entered after the PI was told the row was missing. On all 100 rows, agreement was 79.0% and kappa 0.10 (−0.11 to 0.34). Both versions are reported.

|  | Judges: no violation | Judges: violation |
| --- | --- | --- |
| PI: no violation | 76 | 9 |
| PI: violation | 12 | 3 |

The PI marked 15 responses as violations and the judges 12; they shared 3. Violations are uncommon, which makes kappa unstable, as the wide interval shows.

**Why the agreement was low:** The PI's scoring notes show the sheet's instruction was misread. Some responses were marked as violations because the PI thought the grading rule was wrong or too strict, when the sheet asked only whether the response matched the violation description. In most of the 12 rows where the PI said violation and the judges did not, the specification defined no violation or the response did the opposite of what it described. In the 9 rows where the judges said violation and the PI did not, some judge calls were defensible and some looked wrong. A few items also have unclear rules: the adult versions of one evasion item about a game rating (R072 and R089), R081 (the violation text says only "same as adult") and R077 (the violation text fits the prompt poorly). Items were not corrected and rows were not re-scored.

**Implications:** The audit did not confirm that the AI judges are reliable, but it did not show that they are unreliable: it mostly measured disagreement over how the instruction was read. A second audit was considered and not run. Under the registration, a confirmed claim would need the judge's instructions fixed, a new registration and new data. Until then, treat these results as leads.

## Deviations from the registered plan

There were two departures from the plan and one event handled as registered. A separate [Deviations Log](deviations_log.md) holds the same record.

| Date | What happened | Reason | Effect on results |
| --- | --- | --- | --- |
| Oct 18–19, 2026 | Two gpt-6.1-sol responses (EVAS\_P071, child prompt; one first-run, one second-run) were rejected by the API with a cybersecurity flag and logged as errors. They were recorded as provider blocks. | The registration codes a provider moderation error as a refusal. The pipeline had logged this API error as a generic error, so it was recorded as a block by hand, keeping the provider's message. | Handled as registered, so not a deviation. The registered sensitivity analysis drops all blocks. |
| Oct 19–21, 2026 | The tie-breaker gpt-6-luna became unavailable when OpenAI deactivated the account on Oct 19. 597 tie-break judgments used claude-opus-5-5 instead. The 3,660 earlier tie-breaks stayed with gpt-6-luna. | Account deactivation by the provider, decided before any outcome was analyzed. No appeal was filed. Opus is from the same developer as judge 1, so it is less independent than the registered third-family tie-breaker. | About 2.6% of responses carry an Opus tie-break label. A sensitivity analysis drops them (see Results). The own-family exclusion check also applies. |
| Oct 21, 2026 | Eleven second-run EVAS responses could not be tie-broken because claude-opus-5-5 returned empty replies. | An invalid judge reply is retried once, then that label is treated as missing under the registered rule. | None of the 11 is a first-run response, so primary tests H1–H4 are unaffected. Best-case and worst-case coding were checked. |

One further disclosure concerns the audit: the PI's scoring sheet first came back with row R016 blank, and a second copy filled it in after the PI was told it was missing. Both versions are reported in the audit section.

## Limitations

- **The judges are not verified.** The human audit found low agreement, partly because of a misread instruction, so the grades are unconfirmed and every result is exploratory.
- **Some findings depend on the judge.** The physical-risk result fades with either judge alone, and the credulity result appears with the Gemini judge alone. The strict and lenient definitions point in opposite directions for the violation hypotheses.
- **Judge overlap.** The judges and tie-breaker come from the same families as three of the four evaluated models, so a judge may score its own family more leniently. The own-family exclusion check addresses this and the human audit does not, because it is blind to model identity.
- **Item origin.** The items were generated with claude-sonnet-5-5, which is also an evaluated model, so its results may differ for reasons unrelated to child safety. Child prompts are written by an AI and share wording with adult prompts by design, so they are more fluent than real children's writing.
- **Item checks.** The PI reviewed 100 of 480 items and two raters checked 32, so most items were not individually checked by outside raters. A few items have unclear rules (see the audit section).
- **PI-written specifications.** The PI wrote the grading specifications with AI assistance and scored the audit alone, so the audit is not independent of them. No second audit was run.
- **Sampling.** Three of the four models cannot be run at the planned temperatures, so their results describe default sampling.
- **Power.** With a 4% adult baseline, differences smaller than about five percentage points may be missed.
- **Scope.** The study is US-normed and covers single-turn conversations only. It tests four closed models on the logged access dates, and they cannot be re-run if a provider changes or retires them.
- **Judge substitution.** About 2.6% of grading decisions used a tie-breaker other than the registered one.

## Reproducibility, data release and ethics

The study plan was registered on OSF before the full run, and the registration was approved. The release is planned as an open GitHub repository and this technical report, not a journal paper. The OSF project and the GitHub repository are public. The per-model results table and the item-level labels are held until on or after Nov 28, 2026, so that each provider receives its item-level results at least 30 days before they are released publicly (see the [Deviations Log](deviations_log.md)).

- **Fixed inputs:** the frozen item file and its SHA-256 (above), the pinned model IDs, the judge prompts and rubric, and the analysis script `analyze_childguard.py`. Random seeds: 20261007, 20261008 and 20261009 (review, manipulation check and audit samples) and 20261010 (bootstrap).
- **Pipeline:** a resumable collection and judging script (`childguard_pipeline.py`) that stores every response and judgment with model ID, provider and access date. API keys are kept out of the notebooks and the repository.
- **Records:** this report, the Deviations Log and the registered analysis outputs (first and second run, lenient check and the sensitivity scenarios).

The responses can contain real instructions for bypassing parental controls and other sensitive content. Before release, functional bypass content is redacted from published responses, and the raw audit sheet is kept private. Prompts are synthetic, and no human participants or personal data are involved. The providers' terms of use for publishing model outputs and evaluation results are checked before release.

A claim that models treat children differently would need a new study: fixed judge instructions, a new registration before collecting and new data.
