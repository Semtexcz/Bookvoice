# Update Project Docs From Conversation Summary

Use this prompt when applying a saved conversation summary into the project documentation.

```text
Update the repository documentation using the provided conversation summary.

Read:
- AGENTS.md
- docs/WORKFLOW.md
- docs/CURRENT_STATE.md
- docs/RISKS.md
- docs/ARCHITECTURE.md if architecture changed
- docs/TASK_SEQUENCE.md if tasks changed

Update only relevant files.

Rules:
- Conversation summaries are archival.
- Current facts belong in docs/CURRENT_STATE.md.
- Accepted decisions belong in docs/decisions/.
- Executable work belongs in project/backlog/.
- Risks belong in docs/RISKS.md.
- Do not create tasks for vague ideas.
- Keep changes minimal.
```
