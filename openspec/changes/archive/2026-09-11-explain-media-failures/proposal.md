## Why

The production bot reported only that media could not be processed, without identifying the media, failed stage, provider reason, or recovery action. The administrator needs every problem notification to explain exactly what failed and whether any content was lost.

## What Changes

- Track the processing stage separately for Telegram download, image analysis, and audio transcription.
- Report the media type, filename or Telegram message, stage, human-readable provider reason, impact, and action.
- Treat an empty AI response as an explicit processing failure.
- Keep technical secrets out of notifications while retaining actionable status and provider details.
- Verify that the deployed BotHost instance runs the tested Git revision.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `actionable-error-reporting`: require precise failed-operation and media identification in every media warning.

## Impact

Changes affect `summary_bot/bot.py`, `summary_bot/errors.py`, tests, operational documentation, and the BotHost deployment. No command, database, or environment-variable compatibility changes are required.
