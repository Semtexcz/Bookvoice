# Spec Delta

## Purpose

Lets callers request CEFR-targeted translation and audio-rewrite output without
changing the existing default behavior of the library interfaces.

## ADDED Requirements

### Requirement: Optional proficiency level normalization

The translator and audio-rewriter interfaces SHALL accept an optional keyword-only
`proficiency_level` and SHALL normalize `A0`, `A1`, `A2`, `B1`, `B2`, `C1`, and
`C2` case-insensitively to the uppercase label. Omission SHALL yield `None`.

#### Scenario: Lowercase level is normalized

- **WHEN** a caller passes `proficiency_level="a2"`
- **THEN** the interface uses `A2` for prompt guidance and cache identity

#### Scenario: Every supported level is accepted

- **WHEN** a caller passes any of `A0`, `A1`, `A2`, `B1`, `B2`, `C1`, or `C2` in any letter case
- **THEN** the interface accepts it without error

#### Scenario: Omitted level preserves the legacy path

- **WHEN** a caller omits `proficiency_level`
- **THEN** the interface behaves as it did before the argument existed

#### Scenario: Unsupported level is rejected

- **WHEN** a caller passes a value outside the supported CEFR labels
- **THEN** the interface raises a validation error that names the supported labels

### Requirement: Proficiency guidance in prompts

When a proficiency level is supplied, translation and audio-rewrite prompts SHALL
include the normalized level and SHALL require the model to preserve meaning,
factual information, names, and numbers while adapting vocabulary and sentence
complexity.

#### Scenario: Translation prompt carries the level

- **WHEN** translation runs with `proficiency_level="B1"`
- **THEN** the translation prompt contains `B1` and the preservation constraints

#### Scenario: Rewrite prompt carries the level

- **WHEN** audio rewriting runs with `proficiency_level="A1"`
- **THEN** the rewrite prompt contains `A1` and the preservation constraints

#### Scenario: Default prompts are unchanged

- **WHEN** no proficiency level is supplied
- **THEN** the translation and rewrite prompts contain no proficiency guidance

### Requirement: Proficiency-aware response cache identity

Translation and audio-rewrite response-cache keys SHALL include the normalized
proficiency level so cached responses for different levels never collide, while
case variants of the same level share one entry.

#### Scenario: Different levels use different cache entries

- **WHEN** the same text is processed at `A2` and at `C1`
- **THEN** each level performs its own provider call and stores its own response

#### Scenario: Case variants share a cache entry

- **WHEN** the same text is processed first at `a2` and then at `A2`
- **THEN** the second call reuses the first cached response

#### Scenario: No-level cache identity is preserved

- **WHEN** the same text is processed twice without a proficiency level
- **THEN** the second call reuses the first cached response
