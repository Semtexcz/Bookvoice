# Design

## Context

The translator and audio rewriter are protocol-backed interfaces in
`bookvoice/llm/`, with OpenAI-backed implementations and a deterministic bypass
rewriter. Prompt construction is centralized in `PromptLibrary`, and response-cache
keys are built from provider, model, operation, and a normalized input identity.
The pipeline currently calls both interfaces without a level; this change must not
alter that call path.

See `proposal.md` for motivation and the delta spec for the required behavior.

## Goals / Non-Goals

**Goals:**

- Add the optional level at the interface boundary with a single normalization rule.
- Keep prompt and cache behavior identical when the level is omitted.
- Make cache isolation observable and deterministic in offline tests.

**Non-Goals:**

- CLI options, configuration parsing, pipeline propagation, manifest metadata,
  resume/replay behavior, or TTS prompt changes.
- Any provider call in tests or any change to existing test expectations.

## Decisions

- **One small normalization helper.** A new `bookvoice/llm/proficiency.py` owns the
  supported-label set and `normalize_proficiency_level()`. Both translator and
  rewriter import it, so the accepted values cannot drift between the two
  interfaces. Rejected values raise `ValueError` listing the supported labels.
- **Keyword-only, optional parameter.** Both protocols and their implementations use
  `*, proficiency_level: str | None = None`. Keyword-only keeps existing positional
  calls valid and makes intent explicit at call sites. The deterministic bypass
  rewriter accepts and ignores the argument so it still satisfies the protocol.
- **Prompt guidance only when supplied.** `PromptLibrary` appends a compact CEFR
  instruction block only when a normalized level exists. The existing prompt strings
  remain byte-identical for the omitted path, which preserves legacy behavior and
  avoids changing current outputs.
- **Conditional cache identity.** The normalized level is added to the cache input
  identity only when present. Omitted calls therefore keep their previous identity
  and cache-sharing behavior. Different levels produce different keys; case variants
  normalize to the same key.
- **Test through public interface methods.** Tests patch the provider client and
  inspect prompts and cache counters, so no network or paid model request occurs.

## Risks / Trade-offs

- [Prompt token growth] → Keep the level guidance short and fixed; it adds one
  small paragraph per request.
- [Cache fragmentation] → Levels are an explicit deterministic input, so separate
  entries are correct; omission keeps the old identity.
- [Interface drift] → Both protocols and concrete classes take the same keyword-only
  parameter, and the bypass implementation is covered by a test.
