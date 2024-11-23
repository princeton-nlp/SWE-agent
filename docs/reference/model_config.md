# Models

This page documents the configuration objects used to specify the behavior of a language model (LM).

## Normal LMs

::: sweagent.agent.models.GenericAPIModelConfig
    options:
        heading_level: 3

## Human-in-the-loop models

The following two models allow you to test new commands by prompting you for actions.
This can also be very useful to create your first [demonstrations](../config/demonstrations.md).

::: sweagent.agent.models.HumanModel
    options:
        heading_level: 3

::: sweagent.agent.models.HumanThoughtModel
    options:
        heading_level: 3

## Testing models

::: sweagent.agent.models.ReplayModel
    options:
        heading_level: 3
