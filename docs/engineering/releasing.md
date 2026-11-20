# Releasing aceteam-nodes

The reviewed version-bump PR is the release gate. The `publish.yml` workflow runs on a merge to `main` that changes `pyproject.toml`; other main pushes do not publish. The workflow checks that `pyproject.toml`, `src/aceteam_nodes/__init__.py`, and `uv.lock` agree, requires a nonempty `CHANGELOG.md` section, checks the tag and PyPI state, runs tests, builds and inspects both distributions, and publishes with PyPI trusted publishing and attestations. It creates the annotated tag and GitHub release only after PyPI succeeds. A completed rerun is a no-op; an incomplete release can recover without uploading the same PyPI version twice.

Before merging this workflow, Jason configures the PyPI trusted publisher for owner `aceteam-ai`, repository `aceteam-nodes`, workflow `publish.yml`, and environment `pypi`. The `pypi` environment has no extra reviewer approval. CI receives no PyPI token.

To prepare the next release:

1. Add release notes under `## [<version>]` in `CHANGELOG.md`.
2. Run `scripts/bump-version.sh --patch` (or `--minor`, `--major`, `--rc`, or an explicit version). This updates both source version sites and `uv.lock`; it never publishes, tags, or pushes.
3. Open a draft PR with the version and changelog changes. After review and green CI, a human merges it to start the publish workflow.
4. Verify the PyPI files and attestations, annotated tag, and GitHub release. For an interrupted run, rerun `publish.yml` from the same main commit.

The existing PyPI API token remains available for an authorized emergency release outside CI. Keep it private; do not add it to a GitHub workflow. In a break-glass case, a human verifies the exact built artifacts and uses `uv publish` with the token in a private environment, then records the manual recovery. Routine releases use only OIDC.
