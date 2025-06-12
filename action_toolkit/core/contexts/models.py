from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self, dataclass_transform
from .types import RunnerEnv, GithubEnv

from action_toolkit.internals.env_utils import EnvironmentVariables
from action_toolkit.internals.model import ModelInterface, ModelConfig


@dataclass_transform()
class _ContextModel(ModelInterface):
    model_config = ModelConfig(dataclass_override={'kw_only': True, 'frozen': True, 'slots': True}, exclude_none=True)


@dataclass_transform()
class ActionInfo(_ContextModel):
    path: Path
    ref: str | None = None  # *not exported
    repository: str | None = None
    name: str | None = None


class GithubEnvironment(_ContextModel):
    """Model for GitHub context."""

    action: str | None
    action_path: str | None
    action_ref: str | None  # *not* exported (always None)
    action_repository: str | None
    actor: str | None  # $GITHUB_ACTOR
    actor_id: int | None
    api_url: str | None
    base_ref: str | None
    env_file: str | None  # $GITHUB_ENV path
    event_name: str | None
    event_path: str | None
    graphql_url: str | None
    head_ref: str | None
    job: str | None
    path_file: str | None  # $GITHUB_PATH path
    ref: str | None
    ref_name: str | None
    ref_protected: bool | None
    ref_type: str | None
    repository: str | None
    repository_id: int | None
    repository_owner: str | None
    repository_owner_id: int | None
    retention_days: int | None
    run_id: int | None
    run_number: int | None
    run_attempt: int | None
    secret_source: str | None  # not exported
    server_url: str | None
    sha: str | None
    token: str | None  # GITHUB_TOKEN (may be empty)
    triggering_actor: str | None
    workflow: str | None
    workflow_ref: str | None
    workflow_sha: str | None
    workspace: str | None
    event_json: dict[str, Any] | None

    @classmethod
    def load(cls) -> Self:
        loader = EnvironmentVariables(prefix='GITHUB_')
        action_info = ActionInfo(
            name=loader.get('ACTION', default=None),
            path=loader.get('ACTION_PATH', cast_to=Path),
            ref=loader.get('ACTION_REF', default=None),
            repository=loader.get('ACTION_REPOSITORY', default=None),
        )
