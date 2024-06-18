# Environment variables

!!! hint "Persisting environment variables"
    All environment variables can also be added to `keys.cfg` instead.
    See [here](../installation/keys.md) for more information.

This page details all environment variables that are currently in use by SWE-agent.

* All API keys (for LMs and GitHub) can be set as an environment variable. See [here](../installation/keys.md) for more information.
* `SWE_AGENT_CONFIG_ROOT`: Used to resolve relative paths in the [config](config.md)
* `SWE_AGENT_ENV_LONG_TIMEOUT` (default: 500): Timeout in seconds used for commands that install instance environment.
* `SWE_AGENT_LOG_TIME`: Add timestamps to log (**can only be set as an environment variable**)

!!! warning "Unstable"
    The following variables might still be subject to change

* `SWE_AGENT_COMMUNICATE_METHOD`: Determines how SWE-agent communicates with the running process in the docker container: `end-marker` (default, fast) or `processes` (legacy, slow, more tested)
* `SWE_AGENT_CLONE_METHOD`: `shallow` (default, only retrieves relevant commit) or `full` (clones repository including full history). When using persistent containers or running over multiple problem statements, we fall back to `full`.
* `SWE_AGENT_DOCKER_START_UP_DELAY`: Number of seconds to wait after starting a docker container
