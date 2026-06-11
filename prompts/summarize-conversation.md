# Summarize Project Conversation

Use this prompt after an important project conversation.

```text
Create a concise project update from this conversation.

Output:

1. A conversation summary for:
   docs/conversations/YYYY-MM-DD-short-topic.md

2. Updates for:
   - docs/CURRENT_STATE.md
   - docs/RISKS.md
   - docs/decisions/
   - project/backlog/
   - docs/TASK_SEQUENCE.md if task order changed

Rules:
- Do not invent information.
- Mark open questions clearly.
- Separate decisions from suggestions.
- Convert only concrete next steps into tasks.
- Keep the output concise.
- Repository content must be in English.
```
