---
feature: FEATURE-001
title: "Deterministic audiobook build"
status: planned
created: 2026-03-22
---

# Deterministic audiobook build

## Goal

Provide a deterministic command-line workflow that converts a supported source
book into inspectable text artifacts and audiobook outputs.

## Problem

Long-running source-document conversion can be difficult to inspect, resume,
and verify when intermediate state is not recorded consistently.

## Scope

- extract source text from supported document formats
- split source content into deterministic chapters and chunks
- persist translation, rewrite, audio, and manifest artifacts
- support resumable command-line processing

## Out of Scope

- DRM bypass behavior
- live-provider calls in unit tests
- graphical user interface workflows

## Success Criteria

- [ ] identical inputs produce stable artifact paths and schemas
- [ ] interrupted runs can resume from recorded manifest state
- [ ] tests cover deterministic artifact and command behavior

## Notes

- preserve secret-safe logging
- prefer explicit schemas over loosely shaped dictionaries
- keep provider boundaries mockable in tests
