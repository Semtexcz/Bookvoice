# UML diagrams

PlantUML source files for Bookvoice architecture and flow.

## Files

- `docs/uml/component-overview.puml`: Current module/component dependencies around `bookvoice.pipeline.orchestrator.BookvoicePipeline` and pipeline mixins.
- `docs/uml/pipeline-sequence.puml`: End-to-end `BookvoicePipeline.run` sequence including outline fallback, chunk planning, postprocessing, merge, package, and manifest persistence.
- `docs/uml/domain-model.puml`: Core dataclasses in `bookvoice/models/datatypes.py` including structure-planning and packaged-output types.
- `docs/uml/chapter-chunk-activity.puml`: Activity flow for chapter resolution and chunk planning (outline-first with deterministic fallback).

## Render (optional)

```bash
plantuml docs/uml/*.puml
```
