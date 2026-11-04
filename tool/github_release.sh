#!/usr/bin/env bash
# Create the GitHub release for an existing tag – HACS offers releases as updates
# and shows their version (without a release it shows the commit hash):
#   GITHUB_TOKEN=github_pat_… tool/github_release.sh 0.1.1
# Notes are the version's section of CHANGELOG.md. Uses the gh CLI if installed,
# otherwise the REST API with $GITHUB_TOKEN (fine-grained, Contents: read and write –
# the push-mirror token works).
set -euo pipefail

cd "$(dirname "$0")/.."

repo=exashox/garage-butler-homeassistant

die() { echo "✗ $*" >&2; exit 1; }

version="${1:-}"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "usage: tool/github_release.sh X.Y.Z"
tag="v$version"

notes="$(awk -v h="## [$version]" 'index($0, h) == 1 {f=1; next} /^## \[/{f=0} f' CHANGELOG.md)"
[[ -n "${notes//[[:space:]]/}" ]] || die "CHANGELOG.md has no section [$version]"

if ! command -v gh >/dev/null && [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "! neither gh nor \$GITHUB_TOKEN – create the release by hand (notes: CHANGELOG.md, section $version):"
  echo "  https://github.com/$repo/releases/new?tag=$tag&title=$version"
  exit 1
fi

auth=()
[[ -n "${GITHUB_TOKEN:-}" ]] && auth=(-H "Authorization: Bearer $GITHUB_TOKEN")

# The Gitea push mirror delivers the tag a few seconds after the push.
for _ in $(seq 30); do
  curl -sf -o /dev/null "${auth[@]}" "https://api.github.com/repos/$repo/git/ref/tags/$tag" && break
  sleep 5
done || true
curl -sf -o /dev/null "${auth[@]}" "https://api.github.com/repos/$repo/git/ref/tags/$tag" \
  || die "tag $tag not on GitHub yet – push mirror running? Try again later."

if command -v gh >/dev/null; then
  gh release create "$tag" --repo "$repo" --verify-tag --title "$version" --notes "$notes"
else
  payload="$(python -c 'import json, sys; print(json.dumps({"tag_name": sys.argv[1], "name": sys.argv[2], "body": sys.argv[3]}))' "$tag" "$version" "$notes")"
  curl -sf -o /dev/null -X POST "${auth[@]}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$repo/releases" -d "$payload" \
    || die "GitHub refused the release (token valid, Contents: read and write on $repo?)"
fi

echo "✓ GitHub release $tag"
