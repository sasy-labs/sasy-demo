# Tau2 Airline Benchmark — Translation Variance

Tasks: 36, 43, 47, 48, 49

- **Original spec**: 5 translations
- **Paraphrased spec**: 5 translations
- **reference**: 25 simulations
- **llm_judge_graph**: 25 simulations
- **llm_judge_linear**: 25 simulations
- **llm_judge_graph_weak**: 25 simulations
- **llm_judge_linear_weak**: 25 simulations
- **basic**: 25 simulations

## Per-task pass rate

Translator rows: mean ± std across N translations. Baseline rows: single run pass rate.

| Task | Original | Paraphrased | reference | llm_judge_graph | llm_judge_linear | llm_judge_graph_weak | llm_judge_linear_weak | basic |
|---|---|---|---|---|---|---|---|---|
| 36 | 0.96 ± 0.09 (n=5) | 1.00 ± 0.00 (n=5) | 5/5 | 3/5 | 5/5 | 5/5 | 2/5 | 4/5 |
| 43 | 0.00 ± 0.00 (n=5) | 0.20 ± 0.45 (n=5) | 5/5 | 3/5 | 5/5 | 1/5 | 2/5 | 0/5 |
| 47 | 0.96 ± 0.09 (n=5) | 1.00 ± 0.00 (n=5) | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | 3/5 |
| 48 | 1.00 ± 0.00 (n=5) | 1.00 ± 0.00 (n=5) | 5/5 | 5/5 | 5/5 | 3/5 | 4/5 | 5/5 |
| 49 | 1.00 ± 0.00 (n=5) | 1.00 ± 0.00 (n=5) | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | 5/5 |

## Overall reward

- **Original translations**: 0.784 ± 0.022 (n=5)
- **Paraphrased translations**: 0.840 ± 0.089 (n=5)
- **reference**: 1.000
- **llm_judge_graph**: 0.840
- **llm_judge_linear**: 1.000
- **llm_judge_graph_weak**: 0.680
- **llm_judge_linear_weak**: 0.720
- **basic**: 0.680

## Per-policy detail

### Original translations

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| original_1 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| original_2 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| original_3 | 25 | 0.76 | 5/5 | 0/5 | 4/5 | 5/5 | 5/5 |
| original_4 | 25 | 0.76 | 4/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| original_5 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |

### Paraphrased translations

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| paraphrase_1 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| paraphrase_2 | 25 | 1.00 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| paraphrase_3 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| paraphrase_4 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| paraphrase_5 | 25 | 0.80 | 5/5 | 0/5 | 5/5 | 5/5 | 5/5 |

### Baseline: reference

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| reference | 25 | 1.00 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

### Baseline: llm_judge_graph

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| llm_judge_graph | 25 | 0.84 | 3/5 | 3/5 | 5/5 | 5/5 | 5/5 |

### Baseline: llm_judge_linear

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| llm_judge_linear | 25 | 1.00 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

### Baseline: llm_judge_graph_weak

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| llm_judge_graph_weak | 25 | 0.68 | 5/5 | 1/5 | 4/5 | 3/5 | 4/5 |

### Baseline: llm_judge_linear_weak

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| llm_judge_linear_weak | 25 | 0.72 | 2/5 | 2/5 | 5/5 | 4/5 | 5/5 |

### Baseline: basic

| Policy | Sims | Overall | Task 36 | Task 43 | Task 47 | Task 48 | Task 49 |
|---|---|---|---|---|---|---|---|
| basic | 25 | 0.68 | 4/5 | 0/5 | 3/5 | 5/5 | 5/5 |

