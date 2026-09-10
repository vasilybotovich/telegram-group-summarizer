## Context

Media ingestion and summary publication currently use broad exception handlers. Media alerts discard context, while summary failures escape the group loop.

## Goals / Non-Goals

**Goals:** Human-readable categorization, bounded retries, alert deduplication, and isolation by topic and group.

**Non-Goals:** Persistent incident storage, a monitoring dashboard, or changes to public bot commands.

## Decisions

- Add a small shared error-reporting module instead of a new dependency.
- Retry each remote operation three times with short exponential delays.
- Map common HTTP, timeout, Telegram, and provider failures to Russian explanations while retaining tracebacks in logs.
- Deduplicate alerts in memory for one hour using stable incident keys.
- Delete only messages from topics whose summaries were successfully published.

## Risks / Trade-offs

- In-memory deduplication resets on restart → acceptable because it never hides the first alert after recovery.
- Partial completion needs topic-level deletion → use explicit database deletion scoped by chat, topic, and cutoff.

## Migration Plan

Deploy code without a schema migration, run unit tests, then verify one forced summary. Roll back to the prior commit if notification delivery regresses.
