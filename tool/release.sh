#!/usr/bin/env bash
# Release a version: tool/release.sh 0.2.0
#
# On a clean, pushed develop branch:
#   1. VERSION and manifest.json get the new version,
#      CHANGELOG.md "## [Unveröffentlicht]" becomes "## [0.2.0] – <today>"
#   2. commit "Release 0.2.0" on develop
#   3. fast-forward main to develop, annotated tag v0.2.0
#   4. push develop, main and the tag; back on develop
set -euo pipefail

cd "$(dirname "$0")/.."

die() { echo "✗ $*" >&2; exit 1; }

version="${1:-}"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "usage: tool/release.sh X.Y.Z"
tag="v$version"
current="$(tr -d '[:space:]' < VERSION)"
manifest=custom_components/garagebutler/manifest.json

[[ "$(git branch --show-current)" == develop ]] || die "release from develop"
[[ -z "$(git status --porcelain)" ]] || die "working tree not clean"
git fetch --quiet --tags origin
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/develop)" ]] || die "develop differs from origin/develop"
git merge-base --is-ancestor origin/main HEAD || die "main has commits that are not on develop"
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && die "tag $tag exists"

# Not lower than the current version (equal only for the very first tag).
lowest="$(printf '%s\n%s\n' "$current" "$version" | sort -V | head -1)"
[[ "$lowest" == "$current" ]] || die "$version is lower than $current"

# The unreleased section must not be empty.
notes="$(awk '/^## \[Unveröffentlicht\]/{f=1; next} /^## \[/{f=0} f && NF' CHANGELOG.md)"
[[ -n "$notes" ]] || grep -q "^## \[$version\]" CHANGELOG.md || die "CHANGELOG.md: nothing under [Unveröffentlicht]"

echo "$version" > VERSION
sed -i -E "s/(\"version\": \")[^\"]+\"/\1$version\"/" "$manifest"
if [[ -n "$notes" ]]; then
  sed -i "s/^## \[Unveröffentlicht\]$/## [Unveröffentlicht]\n\n## [$version] – $(date +%F)/" CHANGELOG.md
fi

python -m unittest discover -s tests -q

git add VERSION "$manifest" CHANGELOG.md
git diff --cached --quiet || git commit -q -m "Release $version"
git checkout -q main
git merge -q --ff-only develop
git tag -a "$tag" -m "GarageButler for Home Assistant $version"
git push -q origin develop main "$tag"
git checkout -q develop

echo "✓ $tag released"
