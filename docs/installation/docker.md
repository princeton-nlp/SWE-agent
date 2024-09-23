# Fallback: Usage with docker

Instead of installing SWE-agent from source, you can also run the software directly using Docker.

1. Install Docker ([follow the docs](https://github.com/docker/docker-install) or use the [get-docker.sh script for linux](https://github.com/docker/docker-install)), then start Docker locally. Problems? See [docker issues](tips.md#docker).
2. Run `docker pull sweagent/swe-agent:latest`. *Optional*: If you want to use EnIGMA run also `docker pull sweagent/enigma:latest`.
3. Add your API tokens to a file `keys.cfg` as explained [here](keys.md) or pass them as
   environment variables.

## Running the command line interface

Assuming that you create `keys.cfg` in the current directory, run

```bash
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/keys.cfg:/app/keys.cfg \
  sweagent/swe-agent-run:latest \
  python run.py --image_name=sweagent/swe-agent:latest \
  --model_name gpt4 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml \
  --skip_existing=False
```

For EnIGMA, change the `run.py` arguments as usual:

```bash
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/keys.cfg:/app/keys.cfg \
  sweagent/swe-agent-run:latest \
  python run.py --image_name=sweagent/enigma:latest \
  --model_name gpt4 \
  --data_path /path/to/challenge.json \
  --repo_path /path/to/repo \
  --config_file config/default_ctf.yaml  \
  --skip_existing=False
```

For more information about running EnIGMA please read our [usage instructions](../usage/enigma.md).

<details>
<summary>Output</summary>

```json
--8<-- "docs/usage/cl_tutorial_cmd_1_output.log"
```
</details>

!!! tip "Windows"
    If you're using docker on Windows, use `-v //var/run/docker.sock:/var/run/docker.sock`
    (double slash) to escape it ([more information](https://stackoverflow.com/a/47229180/)).

!!! tip "More tips"
    See the [docker issues section](tips.md#docker) for more help if you run into
    trouble.

If you instead want to pass the keys as environment variables, use

```bash
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  -e GITHUB_TOKEN="yourgithubtoken" \
  -e OPENAI_API_KEY="youropenaikey" \
  sweagent/swe-agent-run:latest \
  # rest of the command above
```

!!! warning "Getting updates"
    Even though the image `sweagent/swe-agent:latest` has the tag `latest`,
    it is not automatically updated every time you run `docker run`. Instead,
    you need to manually run

    ```bash
    docker pull sweagent/swe-agent-run:latest
    docker pull sweagent/swe-agent:latest
    ```

    periodically.

!!! tip "Retrieving generated files"
    The optional `--rm` flag removes the docker container after the command has terminated.
    Therefore, to retrieve files (like generated patch files) from the container, please
    remove this flag.

## Running the web server

!!! tip "Tip"
    Please also read the previous section for tips on passing environment variables
    and staying up to date.

To run the web server, make sure to forward port 3000:

```bash
docker run -p 3000:3000 -it -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/keys.cfg:/app/keys.cfg \
  sweagent/swe-agent-run:latest bash start_web_ui.sh
```

!!! tip "More information"
    See [running the web UI](../usage/web_ui.md) for more information about the
    web UI and additional hints for how to solve problems with the starting it.

{% include-markdown "../_footer.md" %}
