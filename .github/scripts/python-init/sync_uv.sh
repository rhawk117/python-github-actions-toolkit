#!/bin/bash

set -euo pipefail

# Expected Environment Variables:
# - INSTALL_DEV
# - SYNC_LOCKED
# - INSTALL_ALL
# - SHOW_PACKAGES


sync_args=""

if [[ "$SYNC_LOCKED" == "true" ]]; then
    sync_args="$sync_args --locked"
fi

if [[ "$INSTALL_DEV" == "true" ]]; then
    sync_args="$sync_args --dev"
fi

if [[ "$INSTALL_ALL" == "true" ]]; then
    sync_args="$sync_args --all-extras"
fi

echo "::debug::Install command uv sync$sync_args"
uv sync"$sync_args"

if [[ "$SHOW_PACKAGES" == "true" ]]; then
    echo "::group::Package List"
    uv tree --depth 1 | head -n 20
    echo "::endgroup::"
fi