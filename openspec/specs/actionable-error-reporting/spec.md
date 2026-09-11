# actionable-error-reporting Specification

## Purpose
Ensure operational failures are understandable, actionable, and contained without losing unrelated summaries or flooding the administrator.

## Requirements

### Requirement: Contextual notifications
The system SHALL describe the affected group, topic or message, media type and available filename, exact failed operation, human-readable cause, impact, required action, and source link when available. It MUST distinguish Telegram download failures from AI image-analysis and audio-transcription failures, MUST report empty provider responses, and MUST NOT expose credentials or raw secret-bearing payloads.

#### Scenario: Media processing fails
- **WHEN** a supported media item cannot be downloaded or processed after retries
- **THEN** the administrator receives a warning identifying the item, failed operation, understandable cause, impact, recovery action, and source message while confirming that other messages continue to be collected

#### Scenario: Provider returns no usable result
- **WHEN** image analysis or audio transcription returns an empty response
- **THEN** the administrator is told that the provider returned an empty result and that the media was not included in the summary

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
