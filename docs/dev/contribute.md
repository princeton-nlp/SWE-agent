# Contribute to SWE-agent

{%
    include-markdown "../../CONTRIBUTING.md"
    start="<!-- INCLUSION START -->"
    end="<!-- INCLUSION END -->"
%}

Wanna do more and actually contribute code? Great! Please see the following sections for tips and guidelines!

## Development repository set-up

Please install the repository from source, following our [usual instructions](../installation/source.md) but add the `[dev]` option to the `pip` command (you can just run the command again):

```bash
pip install -e '.[dev]'
```

Then, make sure to set up [`pre-commit`](https://pre-commit.com):

```bash
# cd to our repo root
pre-commit install
```

`pre-commit` will check for formatting and basic syntax errors before your commits.

!!! tip "Autofixes"
    Most problems (including formatting) will be automatically fixed.
    Therefore, if `pre-commit`/`git commit` fails on its first run, simply try running it a second time.

    Some more autofixes can be enabled with the `--unsafe-fixes` option from [`ruff`](https://github.com/charliermarsh/ruff):

    ```bash
    pipx run ruff check --fix --unsafe-fixes
    ```

## Running tests

We provide a lot of tests that can be very helpful for rapid development.
Run them with

```bash
pytest
```

Some of the tests might be slower than others. You can exclude them with

```bash
pytest -m "not slow"
```

## Tips for pull requests

* If you see a lot of formatting-related merge conflicts, please make sure that you have `pre-commit` installed.
  To run it over all files, please run `pre-commit run --all-files`.
* Please open separate PRs for separate issues. This makes it easier to incorporate part of your changes.
* It might be good to open an issue and discuss first before investing time on an experimental feature.
* When changing the behavior of the agent, we need to have some indication that it actually improves the success rate of SWE-agent.
  However, if you make the behavior optional without complicating SWE-agent (for example by providing new [commands](../config/commands.md)),
  we might be less strict.
* Please add simple unit tests or integration tests wherever possible. Take a look in the [tests directory](https://github.com/princeton-nlp/SWE-agent/tree/main/tests)
  for inspiration. We emphasize simple easy-tow-rite tests that get a lot of coverage.

## Building the documentation

Simply run

```bash
# cd repo root
mkdocs serve
```

and point your browser to port 8000 or click one of the links in the output.
