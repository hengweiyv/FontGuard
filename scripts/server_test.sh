#!/bin/sh
# Isolated server test run; no published ports and no production-service changes.
set -eu
test_root=${1:-"$HOME/fontguard-tests/2026-10-02"}
cd "$test_root"
tar -xzf fontguard-0.2.0.tar.gz
acceptance_dir=$(mktemp -d "$test_root/acceptance.XXXXXX")
tar -xzf e2e-fonts.tar.gz -C "$acceptance_dir"
docker build --target test -t fontguard-test:0.2.0 ./fontguard-0.2.0 >docker-build.log 2>&1
docker run --rm --memory=1024m --cpus=1 --network=none fontguard-test:0.2.0 >unit-tests.log 2>&1
docker run --rm --memory=1024m --cpus=1 --network=none \
    --entrypoint python -v "$acceptance_dir:/acceptance" \
    fontguard-test:0.2.0 /opt/fontguard/scripts/server_acceptance.py >acceptance.log 2>&1
docker build --target runtime -t fontguard:0.2.0 ./fontguard-0.2.0 >runtime-build.log 2>&1
docker run --rm --memory=512m --cpus=1 --network=none \
    -v "$acceptance_dir/fonts:/workspace:ro" fontguard:0.2.0 \
    scan /workspace --usage webfont --format json --no-cache >runtime-scan.json
cat unit-tests.log
cat acceptance.log
printf 'Acceptance artifacts: %s/results\n' "$acceptance_dir"
