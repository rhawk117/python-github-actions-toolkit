#!/bin/bash

echo "::group::Running ruff checks"
uvx ruff --config .ruff.toml --fix --unsafe-fixes
echo "::endgroup::"

echo "::group::Running ruff format"
uvx ruff format --force-exclude
echo "::endgroup::"