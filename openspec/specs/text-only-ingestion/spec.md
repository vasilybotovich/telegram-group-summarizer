# text-only-ingestion Specification

## Purpose
Ensure summaries are built exclusively from user-visible text while all Telegram attachments remain untouched and unprocessed.

## Requirements

### Requirement: Text-only collection
The system SHALL store only non-empty Telegram message text or non-empty textual captions and MUST NOT download, inspect, transcribe, or describe attached media or files.

#### Scenario: Plain text message
- **WHEN** an active group receives a plain text message from a human participant
- **THEN** the message text is stored for the next summary

#### Scenario: Attachment with a textual caption
- **WHEN** an active group receives an attachment with a non-empty textual caption
- **THEN** only the caption is stored and the attachment is not downloaded or sent to an AI provider

#### Scenario: Attachment without text
- **WHEN** an active group receives an image, audio, voice, video, document, or other attachment without text
- **THEN** the message is silently skipped without retries or administrator warnings

### Requirement: Text-only history import
The system SHALL apply the same text-only collection rules to manually forwarded history.

#### Scenario: Imported attachment without text
- **WHEN** the administrator forwards an attachment without text during an import session
- **THEN** the item is skipped and no media processing is attempted

#### Scenario: Imported attachment with caption
- **WHEN** the administrator forwards an attachment with a textual caption during an import session
- **THEN** only the caption and visible source metadata are imported
