

from ast import TypeVar
from enum import StrEnum
from typing import Literal, Protocol

from action_toolkit.internals.env_utils import EnvironmentVariables, get_type_handler



GithubEnv = Literal[
    "ACTION",                # GITHUB_ACTION
    "ACTION_PATH",           # GITHUB_ACTION_PATH
    "ACTION_REPOSITORY",     # GITHUB_ACTION_REPOSITORY
    "ENV",                   # GITHUB_ENV   (path to env-file)
    "EVENT_NAME",            # GITHUB_EVENT_NAME
    "EVENT_PATH",            # GITHUB_EVENT_PATH
    "GRAPHQL_URL",           # GITHUB_GRAPHQL_URL
    "HEAD_REF",              # GITHUB_HEAD_REF
    "JOB",                   # GITHUB_JOB
    "PATH",                  # GITHUB_PATH  (path to add-path file)
    "REF",                   # GITHUB_REF
    "REF_NAME",              # GITHUB_REF_NAME
    "REF_PROTECTED",         # GITHUB_REF_PROTECTED
    "REF_TYPE",              # GITHUB_REF_TYPE
    "REPOSITORY",            # GITHUB_REPOSITORY
    "REPOSITORY_ID",         # GITHUB_REPOSITORY_ID
    "REPOSITORY_OWNER",      # GITHUB_REPOSITORY_OWNER
    "REPOSITORY_OWNER_ID",   # GITHUB_REPOSITORY_OWNER_ID
    "RETENTION_DAYS",        # GITHUB_RETENTION_DAYS
    "RUN_ID",                # GITHUB_RUN_ID
    "RUN_NUMBER",            # GITHUB_RUN_NUMBER
    "RUN_ATTEMPT",           # GITHUB_RUN_ATTEMPT
    "SERVER_URL",            # GITHUB_SERVER_URL
    "SHA",                   # GITHUB_SHA
    "TOKEN",                 # GITHUB_TOKEN  (job-scoped)
    "TRIGGERING_ACTOR",      # GITHUB_TRIGGERING_ACTOR
    "WORKFLOW",              # GITHUB_WORKFLOW
    "WORKFLOW_REF",          # GITHUB_WORKFLOW_REF
    "WORKFLOW_SHA",          # GITHUB_WORKFLOW_SHA
    "WORKSPACE",             # GITHUB_WORKSPACE
    "ACTOR",                 # GITHUB_ACTOR
    "ACTOR_ID",              # GITHUB_ACTOR_ID
    "API_URL",               # GITHUB_API_URL
    "BASE_REF",              # GITHUB_BASE_REF
]

RunnerEnv = Literal[
    'ARCH', # RUNNER_ARCH
    'DEBUG', # RUNNER_DEBUG
    'ENVIRONMENT', # RUNNER_ENVIRONMENT
    'NAME', # RUNNER_NAME
    'OS', # RUNNER_OS
    'TEMP', # RUNNER_TEMP
    'TOOL_CACHE', # RUNNER_TOOL_CACHE
    'WORKSPACE' # RUNNER_WORKSPACE
]