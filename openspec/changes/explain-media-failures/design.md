## Context

Media download and AI processing currently share one broad exception boundary, so the notifier knows the media type but not which operation failed. Provider exceptions contain useful status information, but notifications must not reproduce arbitrary raw bodies that may be noisy or sensitive.

## Goals / Non-Goals

**Goals:**

- Preserve operation-stage context through retries and reporting.
- Produce a concise Russian notification that is useful without reading logs.
- Verify deployment by exact Git commit, not merely by a successful push.

**Non-Goals:**

- Persist original media or provider payloads.
- Add a general monitoring platform or change the summarization schedule.

## Decisions

- Wrap terminal media failures in a typed error carrying a fixed stage label and the original exception. Fixed labels are safer and clearer than forwarding raw exception text.
- Extract bounded provider facts: HTTP status and known error code/message fields. Map common statuses and transport errors to explicit Russian causes; fall back to the exception class plus a sanitized, length-limited message.
- Derive item identity from Telegram metadata: photo or voice message, or audio/image document filename. Always include the source link when Telegram can construct one.
- Convert empty AI output into an explicit failure rather than silently dropping the message.
- Deploy the tested commit to BotHost and compare the runtime checkout SHA with the GitHub revision.

## Risks / Trade-offs

- [An unknown provider exception may still be generic] → Include the safe exception class/status and retain detailed server logs.
- [A raw exception could contain credentials] → Redact URL credentials, bearer/API-key patterns, and cap the displayed detail.
- [A deployment restart could briefly interrupt polling] → Restart only after tests pass; Telegram retains pending updates.

## Migration Plan

1. Deploy the exact tested commit without database changes.
2. Confirm the process is healthy and its checkout matches the commit.
3. Trigger or simulate representative failures and verify the notification fields.
4. Roll back to the preceding commit if startup or notification delivery regresses.
