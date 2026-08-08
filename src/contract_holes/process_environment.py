from __future__ import annotations

import os


_SENSITIVE_NAMES = frozenset(
    {
        "CI_JOB_JWT",
        "CI_JOB_JWT_V2",
        "DOCKER_AUTH_CONFIG",
        "GPG_AGENT_INFO",
        "KUBECONFIG",
        "SSH_AUTH_SOCK",
    }
)
_SENSITIVE_SUFFIXES = (
    "_ACCESS_KEY_ID",
    "_API_KEY",
    "_AUTH_TOKEN",
    "_CREDENTIALS",
    "_MNEMONIC",
    "_PASSWORD",
    "_PRIVATE_KEY",
    "_RPC_URL",
    "_SECRET",
    "_SECRET_ACCESS_KEY",
    "_SESSION_TOKEN",
    "_TOKEN",
)


def sanitized_subprocess_environment(
    *, remove_prefixes: tuple[str, ...] = ()
) -> dict[str, str]:
    """Copy the environment without common credentials or selected tool settings."""
    environment = os.environ.copy()
    for key in tuple(environment):
        upper = key.upper()
        if (
            upper in _SENSITIVE_NAMES
            or upper.endswith(_SENSITIVE_SUFFIXES)
            or upper.startswith(remove_prefixes)
        ):
            environment.pop(key, None)
    return environment
