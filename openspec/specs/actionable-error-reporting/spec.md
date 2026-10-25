# actionable-error-reporting Specification

## Purpose
Ensure operational failures are understandable, actionable, and contained without losing unrelated summaries or flooding the administrator.

## Requirements

### Requirement: Failure isolation
The system SHALL continue processing unrelated topics and groups after a local failure.

#### Scenario: One topic summary fails
- **WHEN** one topic cannot be summarized
- **THEN** its messages remain stored while other due topics and groups are processed

### Requirement: Noise control
The system SHALL retry transient operations and suppress repeated equivalent alerts for a cooldown period.

#### Scenario: Temporary provider failure
- **WHEN** an AI provider succeeds during an automatic retry
- **THEN** no administrator warning is sent

### Requirement: Summary failure notifications
The system SHALL describe the affected group or topic, failed summary operation, human-readable cause, impact, and required action. It MUST NOT expose credentials or raw secret-bearing payloads. Skipped attachments MUST NOT produce failure notifications.

#### Scenario: Summary generation fails
- **WHEN** a topic summary cannot be generated after retries
- **THEN** the administrator receives a warning identifying the group or topic, understandable cause, impact, and recovery behavior

#### Scenario: Attachment is skipped
- **WHEN** a message has no textual content and is skipped
- **THEN** the administrator receives no failure notification
