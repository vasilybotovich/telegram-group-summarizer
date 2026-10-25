## 1. Text-only ingestion

- [x] 1.1 Centralize extraction of message text and captions and verify unit tests reject empty or attachment-only messages
- [x] 1.2 Remove live and imported media-processing branches and verify handlers never call Telegram download or media AI methods

## 2. Remove obsolete media support

- [x] 2.1 Remove image/audio methods, ASR configuration, and media-specific error reporting and verify source search finds no processing references
- [x] 2.2 Update user guidance and README and verify documentation consistently describes text-only behavior

## 3. Verification and release

- [x] 3.1 Run formatting/static checks, full tests, and OpenSpec validation successfully
- [x] 3.2 Archive the validated OpenSpec change and verify the resulting specification set
- [x] 3.3 Commit and push the change, then verify the deployed bot revision when deployment access is available
