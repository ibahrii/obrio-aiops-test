#!/usr/bin/env bash
# Regenerate every table in eval/results/ from the on-disk cache (no API calls).
# Assistant v1 results are kept as the historical record (produced with earlier guard code, see PROMPT_LOG.md).
set -euo pipefail
cd "$(dirname "$0")/.."

for v in v1 v2 v3 v4; do
  python eval/run_eval.py --model gemini-flash-lite --prompt "$v" --cache-only >/dev/null
done
for v in v1 v2; do  # v3 was not run on Groq (free-tier daily token budget); v4 is run below
  python eval/run_eval.py --model groq-gpt-oss-120b --prompt "$v" --cache-only >/dev/null
done
for v in v2 v3 v4; do
  python eval/run_eval.py --model gemini-flash-lite --prompt "$v" --dataset holdout --cache-only >/dev/null
done
for m in gemini-flash gemini-flash-3.6 groq-gpt-oss-120b groq-gpt-oss-20b openrouter-nemotron-free; do
  python eval/run_eval.py --model "$m" --prompt v4 --cache-only >/dev/null
  python eval/run_eval.py --model "$m" --prompt v4 --dataset holdout --cache-only >/dev/null
done
for m in gemini-flash-lite groq-gpt-oss-120b; do  # noisy-text robustness set (data/tickets_noisy.jsonl)
  python eval/run_eval.py --model "$m" --prompt v4 --dataset noisy --cache-only >/dev/null
done
python eval/run_eval.py --model gemini-flash-lite --prompt v4 --dataset holdout2 --cache-only >/dev/null
for d in eval holdout noisy holdout2; do  # rejected prompt v5 (see PROMPT_LOG.md)
  python eval/run_eval.py --model gemini-flash-lite --prompt v5 --dataset "$d" --cache-only >/dev/null
done
python eval/compare_models.py >/dev/null
python eval/run_assistant_eval.py --model gemini-flash-lite --prompt v2 --cache-only >/dev/null
python eval/cost_report.py >/dev/null
python eval/simulate_failures.py >/dev/null
python -m pytest -q tests
echo "done: eval/results/ regenerated from cache"
