"""Snapshot public paid-tier prices for the models we use.

Source: OpenRouter endpoints API (https://openrouter.ai/api/v1/models/{id}/endpoints),
which lists each upstream provider's own per-token price (Google AI Studio, Groq,
DeepInfra). OpenRouter passes provider prices through without markup, so the
"Google AI Studio" / "Groq" rows are the providers' public paid prices.

Run: python eval/fetch_prices.py  -> eval/results/pricing_snapshot.json
"""
import datetime as dt
import json
import pathlib

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "results" / "pricing_snapshot.json"

# openrouter model id -> provider tag we bill against
TARGETS = {
    "google/gemini-3.8-flash": "google-ai-studio",
    "google/gemini-3.6-flash": "google-ai-studio",
    "google/gemini-3.5-flash-lite": "google-ai-studio",
    "openai/gpt-oss-120b": "groq",
    "openai/gpt-oss-20b": "groq",
    "nvidia/nemotron-3-ultra-550b-a55b": "deepinfra/fp4",
}


def main() -> None:
    snapshot = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "source": "https://openrouter.ai/api/v1/models/{id}/endpoints", "models": {}}
    for model_id, tag in TARGETS.items():
        r = httpx.get(f"https://openrouter.ai/api/v1/models/{model_id}/endpoints", timeout=30)
        r.raise_for_status()
        endpoints = r.json()["data"]["endpoints"]
        rows = []
        for e in endpoints:
            p = e["pricing"]
            rows.append({
                "provider": e.get("provider_name"),
                "tag": e.get("tag"),
                "input_per_1m": round(float(p["prompt"]) * 1e6, 4),
                "output_per_1m": round(float(p["completion"]) * 1e6, 4),
                "cached_input_per_1m": round(float(p.get("input_cache_read") or 0) * 1e6, 4),
            })
        chosen = next((x for x in rows if x["tag"] == tag), None)
        snapshot["models"][model_id] = {"billing_tag": tag, "chosen": chosen, "all_endpoints": rows}
        print(model_id, chosen)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
    print("saved", OUT)


if __name__ == "__main__":
    main()
