#!/bin/bash
# release.sh — Resumable release automation for aceteam-nodes
#
# Each step checks if it already completed and skips if so,
# making the script safe to re-run after partial failures.
#
# Usage:
#   ./scripts/release.sh -v v0.2.0 -y      # Non-interactive
#   ./scripts/release.sh --dry-run -v v0.2.0
#   ./scripts/release.sh -h

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

VERSION=""
AUTO_CONFIRM=false
DRY_RUN=false

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Resumable release automation for aceteam-nodes."
    echo "Safe to re-run — each step skips if already completed."
    echo ""
    echo "Options:"
    echo "  -v, --version VERSION   Version to release (e.g., v0.2.0)"
    echo "  -y, --yes               Auto-confirm without prompting"
    echo "  --dry-run               Show what would be done without executing"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  UV_PUBLISH_TOKEN    PyPI API token (required for publishing)"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version) VERSION="$2"; shift 2 ;;
        -y|--yes) AUTO_CONFIRM=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help) print_help; exit 0 ;;
        *) echo -e "${RED}Error: Unknown option: $1${NC}"; print_help; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Release Automation: aceteam-nodes"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}   (DRY RUN MODE)${NC}"
fi
echo ""

# --- Prerequisites ---
for cmd in gh uv git; do
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed.${NC}"
        exit 1
    fi
done

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo -e "${BLUE}Loading environment from .env${NC}"
    set -a  # automatically export all variables
    source .env
    set +a
fi

if [[ "$DRY_RUN" != true && -z "${UV_PUBLISH_TOKEN:-}" ]]; then
    echo -e "${YELLOW}Warning: UV_PUBLISH_TOKEN is not set. Publishing to PyPI will fail.${NC}"
fi

# --- Version ---
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
if [ -z "$VERSION" ]; then
    echo -e "${YELLOW}Current version: $CURRENT_VERSION${NC}"
    read -p "Enter new version (e.g., v0.2.0): " VERSION
fi

if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    echo -e "${RED}Error: Invalid version format (expected v0.2.0 or v0.2.0-rc1)${NC}"
    exit 1
fi

VERSION_NUM="${VERSION#v}"

# --- Change Summary ---
TAG_EXISTS=false
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    TAG_EXISTS=true
    echo -e "${YELLOW}Tag $VERSION already exists — will resume from where we left off${NC}"
fi

if [ "$CURRENT_VERSION" != "v0.0.0" ] && [ "$TAG_EXISTS" != true ]; then
    COMMIT_LOG=$(git log "$CURRENT_VERSION"..HEAD --pretty=format:"- %s" --no-merges)
    COMMIT_COUNT=$(git rev-list --count "$CURRENT_VERSION"..HEAD)
else
    COMMIT_LOG=$(git log --pretty=format:"- %s" --no-merges -20)
    COMMIT_COUNT="N/A (initial release)"
fi

echo ""
echo "Release Summary:"
echo "   Version: $VERSION"
echo "   Commits: $COMMIT_COUNT"
echo ""

if [[ "$AUTO_CONFIRM" != true ]]; then
    read -p "Continue? (y/N): " -n 1 -r; echo ""
    [[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }
fi

# ── Step 1: Update version ──────────────────────────────────────────
echo ""
echo -e "${GREEN}Step 1/6: Update version to $VERSION_NUM${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}[DRY-RUN] Would update pyproject.toml and __init__.py${NC}"
else
    sed -i "s/^version = \".*\"/version = \"$VERSION_NUM\"/" pyproject.toml
    sed -i "s/^__version__ = \".*\"/__version__ = \"$VERSION_NUM\"/" src/aceteam_nodes/__init__.py
    echo "Done"
fi

# ── Step 2: Build ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Step 2/6: Build sdist + wheel${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}[DRY-RUN] Would run: uv sync${NC}"
    echo -e "${BLUE}[DRY-RUN] Would run: uv build${NC}"
else
    rm -rf dist/
    uv sync
    uv build
    echo "Done"
fi

# ── Step 3: Git commit + tag + push ────────────────────────────────
echo ""
echo -e "${GREEN}Step 3/6: Git commit + tag + push${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}[DRY-RUN] Would commit, tag $VERSION, and push${NC}"
else
    # Commit version bump if needed
    git add pyproject.toml src/aceteam_nodes/__init__.py
    if git diff --cached --quiet; then
        echo "No version changes to commit"
    else
        git commit -m "release: $VERSION"
    fi

    # Tag if needed
    if git rev-parse "$VERSION" >/dev/null 2>&1; then
        echo "Tag $VERSION already exists, skipping"
    else
        git tag -a "$VERSION" -m "$VERSION"
    fi

    # Push branch + tag
    git push origin "$(git branch --show-current)" 2>&1 || true
    git push origin "$VERSION" 2>&1 || true
    echo "Done"
fi

# ── Step 4: Publish to PyPI ─────────────────────────────────────────
echo ""
echo -e "${GREEN}Step 4/6: Publish to PyPI${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}[DRY-RUN] Would run: uv publish${NC}"
else
    # Check if already published
    if curl -sf "https://pypi.org/pypi/aceteam-nodes/$VERSION_NUM/json" > /dev/null 2>&1; then
        echo "Already published to PyPI, skipping"
    else
        uv publish
    fi
    echo "Done"
fi

# ── Step 5: GitHub release ──────────────────────────────────────────
echo ""
echo -e "${GREEN}Step 5/6: Create GitHub release${NC}"

RELEASE_NOTES="## What's New

$COMMIT_LOG

## Installation

\`\`\`bash
pip install aceteam-nodes==$VERSION_NUM
\`\`\`

Or with uv:

\`\`\`bash
uv pip install aceteam-nodes==$VERSION_NUM
\`\`\`

## Links

- [PyPI](https://pypi.org/project/aceteam-nodes/$VERSION_NUM/)
- [Documentation](https://github.com/aceteam-ai/aceteam-nodes#readme)"

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}[DRY-RUN] Would create GitHub release with dist/ artifacts${NC}"
else
    if gh release view "$VERSION" >/dev/null 2>&1; then
        echo "GitHub release $VERSION already exists, skipping"
    else
        gh release create "$VERSION" \
            --title "$VERSION" \
            --notes "$RELEASE_NOTES" \
            dist/*
    fi
    echo "Done"
fi

# ── Step 6: Summary ─────────────────────────────────────────────────
echo ""
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${GREEN}Dry run complete${NC}"
    echo "  Run: $0 -v $VERSION -y"
else
    RELEASE_URL=$(gh release view "$VERSION" --json url -q .url 2>/dev/null || echo "N/A")
    echo -e "${GREEN}Release $VERSION complete!${NC}"
    echo ""
    echo "  GitHub: $RELEASE_URL"
    echo "  PyPI:   https://pypi.org/project/aceteam-nodes/$VERSION_NUM/"
fi
