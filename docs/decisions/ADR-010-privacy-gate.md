# ADR 010. Check every outgoing tree and identity

**Context.** SEC requests require an identifying User-Agent. The public repository uses a separate Git noreply identity.

**Decision.** Keep the local SEC identity in ignored configuration and the Action identity in a secret. Strip headers recursively. Before each push scan tracked content and check every outgoing snapshot, commit message, author and committer.

**Alternatives.** Checking the working tree alone could miss private text or metadata in an earlier outgoing commit.

**Consequences.** A failing check stops publication. The tracked-file test reads every file type, including CSV, PNG, HTML and JSON records.

[Push gate](../../scripts/check_push_privacy.py) · [Privacy tests](../../tests/test_guidance_privacy.py)
