"""Cost model: real token counts from eval runs x public paid-tier prices."""
from __future__ import annotations

from . import config


def call_cost(model_key: str, in_tokens: int, out_tokens: int, prices: dict | None = None,
              cached_in_tokens: int = 0) -> float:
    """USD for one call. out_tokens already include thinking/reasoning tokens (billed as output)."""
    prices = prices or config.load_prices()
    p = prices[model_key]
    fresh_in = max(in_tokens - cached_in_tokens, 0)
    return (fresh_in * p["input"] + cached_in_tokens * p["cached_input"] + out_tokens * p["output"]) / 1e6


def monthly(cost_per_ticket: float, tickets: int = 10_000) -> float:
    return cost_per_ticket * tickets


def cascade_cost(cheap: dict, strong: dict, escalation_rate: float) -> float:
    """cheap/strong = {'cost': per-ticket USD}. Escalated tickets pay for both calls."""
    return cheap["cost"] + escalation_rate * strong["cost"]


def with_prompt_cache(model_key: str, in_tokens: int, out_tokens: int, static_tokens: int,
                      prices: dict | None = None) -> float:
    """Cost if the static prefix (system prompt, taxonomy, few-shot, KB) is served from the provider's prompt cache.
    Ignores cache-storage fees (Gemini explicit caching bills storage per hour; implicit caching does not)."""
    return call_cost(model_key, in_tokens, out_tokens, prices, cached_in_tokens=min(static_tokens, in_tokens))
