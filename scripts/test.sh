#!/bin/bash

echo "::group::Running Tests"

uvx pytest --cov=action_toolkit .

echo "::endgroup::"
