# Installation from source

Installation from source is the preferred way to set up SWE-agent on your machine.

!!! warning "Issues on Windows"
    Expect some issues with Windows (we're working on them).
    In the meantime, use Docker (see below).

1. [Install Docker](https://docs.docker.com/engine/install/), then start Docker locally.
2. For the web interface only: Install [`nodejs`][nodejs-install].
3. Clone this repository.
4. Run `pip install --editable .` at the repository root (as with any python setup, it's recommended to use [conda][] or [virtual environments][] to manage dependencies).
5. Run `./setup.sh` to create the `swe-agent` docker image.
6. Create a `keys.cfg` file at the root of this repository ([more information](keys.md)).

[nodejs-install]: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm

!!! tip "Docker issues"
    If you run into docker issues, see the [installation tips section](tips.md) for more help

[conda]: https://docs.conda.io/en/latest/
[virtual environments]: https://realpython.com/python-virtual-environments-a-primer/