# Build your own agent Docker image

This section is about modifying the Docker image in which we run the commands suggested by the agent.

There are two reasons to build your own Docker image

1. You need a very specific environment to install your package (anything that you cannot simply install inside of a conda environment)
2. You want to pre-install your package for [speedup](../usage/cl_tutorial.md#speedup).

There are three steps involved:

1. Modify the [`swe.Dockerfile` Dockerfile](https://github.com/princeton-nlp/SWE-agent/blob/main/docker/swe.Dockerfile) (also shown below).
   We provide some extended explanation of the Dockerfile [here](https://github.com/princeton-nlp/SWE-agent/blob/main/docker/README.md).
2. Build the image. One way is to simply run `./setup.sh`. Alternatively, especially if you want to change the default tag (`sweagent/swe-agent:latest`), run
   ```bash
   docker build -t "YOUR TAG HERE" -f docker/swe.Dockerfile \
     --build-arg TARGETARCH=$(uname -m) .
   ```
3. Make sure you use the new image by passing the `--image_name` flag to `run.py`.

Default Dockerfile:

```Dockerfile
--8<-- "docker/swe.Dockerfile"
```