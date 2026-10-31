# Changelog

## Protocol 1.2 Pilot

- Replaced bwrap/host controls with fail-closed Docker cgroup isolation and mandatory preflight.
- Added safe regular-file reads, symlink/special-file rejection and size limits.
- Removed trusted host mode and in-process candidate acceptance reporting.
- Required signed, hash-bound runner and blinded-reviewer attestations.
- Made pair comparison verify both exact standard trees and scenario/repeat.
- Made mutation expectations exact sets rather than subsets.
- Agent runs remain 0/4; no superiority claim.
