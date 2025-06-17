#!/bin/bash

set -euo pipefail

echo "::group::Running Tests"

uv run pytest --cov=action_toolkit .

echo "::endgroup::"
