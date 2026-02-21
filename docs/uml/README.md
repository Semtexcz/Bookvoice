# UML diagrams

PlantUML source files for Bookvoice architecture and flow.

## Files

- `docs/uml/component-overview.puml`: Component-level module dependencies.
- `docs/uml/pipeline-sequence.puml`: End-to-end sequence of `BookvoicePipeline.run`.
- `docs/uml/domain-model.puml`: Core dataclasses in `bookvoice/models/datatypes.py`.
- `docs/uml/chapter-chunk-activity.puml`: Activity flow for chapter split and chunk generation.

## Render (optional)

```bash
plantuml docs/uml/*.puml
```
