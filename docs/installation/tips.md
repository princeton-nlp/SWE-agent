# More installation tips

## Docker issues <a name="docker"></a>

First, test if you can use docker in general, for example by running

```bash
docker run hello-world
```

If you get an error like

```
docker: permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Head "http://%2Fvar%2Frun%2Fdocker.sock/_ping": dial unix /var/run/docker.sock: connect: permission denied.
```

* Make sure that you allow the use of the Docker socket. In Docker desktop, click *Settings* > *Advanced* > *Allow the default Docker socket to be used (requires password)*.
* On the command line, you can try `sudo chmod 666 /var/run/docker.sock` or add your user to the `docker` linux user group
* If your docker installation uses a different socket, you might have to symlink them, see [this command for example](https://github.com/princeton-nlp/SWE-agent/issues/20#issuecomment-2047506005)

If you are using any containers from dockerhub (i.e., you ran `docker pull ...` or you are running `docker run ...`), please make sure that you are using the latest
versions. Just because an image has the `latest` tag (e.g., `sweagent/swe-agent-run:latest`) does not mean that it will auto-update. Please run
`docker pull sweagent/swe-agent-run:latest` to make sure you actually have the most recent version!

Any remaining issues? Please [open a GitHub issue](https://github.com/princeton-nlp/SWE-agent/issues/new/choose)!
