## Context

The Telegram handlers currently branch into media download and AI recognition before persistence. The same branch is used for live collection and history import. See proposal.md for the motivation to remove it.

## Goals / Non-Goals

**Goals:**
- Make text extraction a single, deterministic gate before database writes.
- Ensure media bytes never leave Telegram through this bot.
- Keep captions because they are explicit user-authored text.

**Non-Goals:**
- Change summary generation, scheduling, database schema, or command behavior.
- Recover text embedded inside images, audio, video, or documents.

## Decisions

1. Use only Telegram's text and caption fields. This is simpler and auditable compared with MIME allowlists, which can miss new attachment types.
2. Remove media methods and ASR configuration rather than leave dormant code. This prevents accidental reactivation and makes the privacy boundary explicit.
3. Silently skip non-text messages. They are valid Telegram activity, not operational failures.
4. Keep generic retry and summary-failure reporting because AI is still used to summarize stored text.

## Risks / Trade-offs

- [Useful information exists only inside an attachment] → The summary intentionally omits it; users can add a text caption when needed.
- [Deploying an older image restores media processing] → Verify the deployed revision and run regression tests before release.

## Migration Plan

1. Deploy the text-only revision without a database migration.
2. Verify plain text and captions are stored while attachment-only messages are skipped.
3. Roll back to the previous image only if summary collection itself regresses; note that rollback restores media processing.
