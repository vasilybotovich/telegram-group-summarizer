## 1. Diagnostic reporting

- [x] 1.1 Add stage-aware media failures and safe provider-reason extraction; verify unit tests cover download, provider status, timeout, and empty response cases
- [x] 1.2 Add media identity to administrator notifications; verify tests cover photo, voice, filename, group, topic, and source link

## 2. Integration and documentation

- [x] 2.1 Wire stage-aware processing into live and imported media flows; verify all tests pass
- [x] 2.2 Update operational documentation and archive the validated OpenSpec change

## 3. Production deployment

- [x] 3.1 Commit and push the complete change; verify the remote branch points to the tested commit
- [x] 3.2 Deploy or restart the BotHost bot and verify its runtime Git SHA, process health, and logs
