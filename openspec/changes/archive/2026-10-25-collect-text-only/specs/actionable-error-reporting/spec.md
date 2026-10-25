## ADDED Requirements

### Requirement: Summary failure notifications
The system SHALL describe the affected group or topic, failed summary operation, human-readable cause, impact, and required action. It MUST NOT expose credentials or raw secret-bearing payloads. Skipped attachments MUST NOT produce failure notifications.

#### Scenario: Summary generation fails
- **WHEN** a topic summary cannot be generated after retries
- **THEN** the administrator receives a warning identifying the group or topic, understandable cause, impact, and recovery behavior

#### Scenario: Attachment is skipped
- **WHEN** a message has no textual content and is skipped
- **THEN** the administrator receives no failure notification

## REMOVED Requirements

### Requirement: Contextual notifications
**Reason**: Media download and recognition were removed because the bot now collects only explicit Telegram text.

**Migration**: Use the new Summary failure notifications requirement for failures that can still occur while creating text summaries. Attachment-only messages are silently skipped.
