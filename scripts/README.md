# Scripts

Scripts should handle mechanical operations only. Keep business judgment in scenario documents and task records.

Recommended first scripts:

- `repo-status`: report branch, dirty state, and recent commits for affected repos.
- `prepare-branches`: create or switch branches after checking dirty state.
- `run-repo-checks`: run checks listed in `manifests/repos.yaml`.
- `run-integration-checks`: run scenario-specific cross-repo smoke tests.
- `collect-diff-summary`: summarize changed files and diff stats for affected repos.

Add scripts after the manual workflow has been validated.
