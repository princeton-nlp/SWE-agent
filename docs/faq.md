# Frequently Asked Questions

> What models are supported?

Probably all of them! There's even a few for testing. See [models](../installation/keys.md).

> What's up with all the output files?

You're probably most interested in the `*.traj` files, which contain complete records of SWE-agent's thought process and actions. See [output files](usage/trajectories.md) for more information.

> How can I change the demonstrations given to SWE-agent?

At the start of each run, we feed the agent a demonstration trajectory, showing it how to solve an example issue.
This substantially improves the agent's abilities to solve novel issues.
If you'd like to modify or totally change this demonstration, to better fit your use case, see [this](config/demonstrations.md).

> Does SWE-agent run on Windows/MacOS/Linux?

Yes! Your only limitation might be the availability of the docker containers for your environments.
But you can always execute SWE-agent in the cloud.

> I got a very long error message about various configuration options not working. What's up?

This is probably because of union types.
See [this section](#union-types) for more information, but the short version is that some options (e.g., the repository or problem statement) can be specified in multiple ways, so we try every option until we find the one that works based on your inputs.
If none of them work, we throw an error which then tells you why we cannot initialize any of the types, so this will get somewhat long and confusing.

{% include-markdown "_footer.md" %}