# TODO

These items are candidates for future work, not authorization to begin. Propose them to the user and obtain permission before proceeding.

- [ ] Set up `https://archpilot.messybox.fyi` as the short bootstrap URL using Cloudflare.
  - Confirm the DNS, HTTPS and redirect configuration for the hostname.
  - Redirect to the published Archpilot installer on GitHub Releases.
  - Verify that `curl -fsSL https://archpilot.messybox.fyi | bash` installs and launches Archpilot in a disposable Arch VM.
  - Update the README with the verified command and document how to update the redirect for future releases.
