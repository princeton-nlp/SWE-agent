# Installation from source

Installation from source is the preferred way to set up SWE-agent on your machine.

!!! warning "Issues on Windows"
    Expect some issues with Windows (we're working on them).
    In the meantime, [use Docker](docker.md).

1. [Install Docker](https://docs.docker.com/engine/install/), then start Docker locally.
2. If you plan on using the web-based GUI: Install [`nodejs`][nodejs-install].
3. Clone the repository, for example with
    ```bash
    git clone https://github.com/princeton-nlp/SWE-agent.git
    ```
4. Run
    ```
    pip install --editable .
    ```
    at the repository root (as with any python setup, it's recommended to use [conda][] or [virtual environments][] to manage dependencies). Error about editable install? Please update pip[^1].
5. Run
    ```bash
    docker pull sweagent/swe-agent:latest
    ```
Alternatively, you can run `./setup.sh` to create your own `swe-agent` docker image.
6. Set up your LM API keys as explained [here](keys.md).

[nodejs-install]: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm

!!! tip "Docker issues"
    If you run into docker issues, see the [installation tips section](tips.md) for more help.

!!! tip "Updating"
    SWE-agent is still in active development. Features and enhancement are added often.
    To make sure you are on the latest version, periodically run `git pull`
    (there is no need to redo the `pip install`).
    You might also want to run `docker pull sweagent/swe-agent:latest` periodically
    (though changes to the container are more rare).

!!! note "Development setup"
    Want to modify SWE-agent? Great! There are a few extra steps and tips:
    Please check our [contribution guide](../dev/contribute.md).

[conda]: https://docs.conda.io/en/latest/
[virtual environments]: https://realpython.com/python-virtual-environments-a-primer/

[^1]: You can update `pip` with `pip install --upgrade pip`.

{% include-markdown "../_footer.md" %}
