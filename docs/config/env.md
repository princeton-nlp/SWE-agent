# Environment variables

!!! hint "Persisting environment variables"
    All environment variables can also be added to `keys.cfg` instead.
    See [here](../installation/keys.md) for more information.

This page details all environment variables that are currently in use by SWE-agent.

* All API keys (for LMs and GitHub) can be set as an environment variable. See [here](../installation/keys.md) for more information.
* [Experimental] `SWE_AGENT_EXPERIMENTAL_COMMUNICATE` switches to a faster way of communicating with running docker
  shell sessions. This has not been tested on SWE-bench, so it might sometimes break.
  However, it can be very useful when running on single issues.
* [Experimental] `SWE_AGENT_EXPERIMENTAL_CLONE`: Uses sparse clones
* `SWE_AGENT_DOCKER_START_UP_DELAY`: Number of seconds to wait after starting a docker container
* `SWE_AGENT_CONFIG_ROOT`: Used to resolve relative paths in the [config](config.md)