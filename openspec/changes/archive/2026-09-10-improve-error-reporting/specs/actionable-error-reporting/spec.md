## Purpose

Ensure operational failures are understandable, actionable, and contained without losing unrelated summaries or flooding the administrator.

## ADDED Requirements

### Requirement: Contextual notifications
The system SHALL describe the affected group, topic or message, human-readable cause, impact, required action, and source link when available.

#### Scenario: Media processing fails
- **WHEN** a supported media item cannot be processed after retries
- **THEN** the administrator receives a warning identifying the item and confirming that other messages continue to be collected

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
