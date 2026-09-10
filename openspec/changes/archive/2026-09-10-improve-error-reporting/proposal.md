## Why

Current failure notifications hide the affected message, human-readable cause, impact, and required action. A failure in one topic can also interrupt summaries for unrelated topics or groups.

## What Changes

- Classify media and summary failures into clear user-facing categories.
- Retry transient AI and Telegram failures before notifying the administrator.
- Include group, topic/message context, impact, and required action in notifications.
- Isolate failures so processing continues for other topics and groups.
- Preserve failed messages for a later summary attempt and suppress duplicate alerts.

## Capabilities

### New Capabilities

- `actionable-error-reporting`: Human-readable, contextual, severity-based notifications and resilient processing.

### Modified Capabilities


## Impact

Touches Telegram media ingestion, scheduled summary generation, administrator notifications, tests, and operational documentation. No public command or configuration compatibility break is intended.
