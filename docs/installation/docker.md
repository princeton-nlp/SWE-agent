# Fallback: Usage with docker

!!! warning "Limitations"
    The latest containerized version does not yet provide the web interface.

Instead of installing SWE-agent from source, you can also run the software directly using Docker. 

1. [Install Docker](https://docs.docker.com/engine/install/), then start Docker locally.
2. Run `docker pull sweagent/swe-agent:latest`
3. Add your API tokens to a file `keys.cfg` as explained [here](keys.md)

Then run

```bash
# NOTE:
# This assumes that keys.cfg is in your current directory (else fix the path below)
# This command is equivalent to the script shown in the quickstart 
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/keys.cfg:/app/keys.cfg \
  sweagent/swe-agent-run:latest \
  python run.py --image_name=sweagent/swe-agent:latest \
  --model_name gpt4 \
  --data_path https://github.com/pvlib/pvlib-python/issues/1603 \
  --config_file config/default_from_url.yaml  --skip_existing=False
```

!!! tip "Tips"
    * For more information on the different API keys/tokens, see [below](keys.md).
    * If you're using docker on Windows, use `-v //var/run/docker.sock:/var/run/docker.sock`
    (double slash) to escape it ([more information](https://stackoverflow.com/a/47229180/)).
    * See the [installation issues section](tips.md) for more help if you run into
    trouble.
  
{% include-markdown "../_footer.md" %}