# TODO

These items are candidates for future work, not authorization to begin. Propose them to the user and obtain permission before proceeding.

Both the items themselves and their implementation approaches are open to challenge. Propose changes to priorities, scope or technical approaches with a clear rationale; discuss alternatives with the user before acting.

- [ ] Cover at least the same installation steps as `archinstall`.
  - Review the current `archinstall` workflow and document its steps and configuration choices as a coverage checklist.
  - Compare Archpilot against that checklist, identify gaps, and propose an implementation plan for user approval.
  - Validate coverage in disposable VMs, including installation execution and a successful first boot.

- [ ] Set up `https://archpilot.messybox.fyi` as the short bootstrap URL using Cloudflare.
  - Confirm the DNS, HTTPS and redirect configuration for the hostname.
  - Redirect to the published Archpilot installer on GitHub Releases.
  - Verify that `curl -fsSL https://archpilot.messybox.fyi | bash` installs and launches Archpilot in a disposable Arch VM.
  - Update the README with the verified command and document how to update the redirect for future releases.
