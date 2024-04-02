# Docker
To ensure reproducibility and sandboxed execution of SWE-agent actions across systems, we adopt practices established in [prior work](https://intercode-benchmark.github.io/) and use [🐋 Docker](https://www.docker.com/) containers to carry out SWE-agent inference.

* The `swe.Dockerfile` file is the customized image written for the environment of SWE-agent.
* The `./setup.sh` script automatically builds this image.
* When `run.py` is invoked, containers are automatically created from the built image.
    * There is no need to manually build a container from the image.

Here, we explain what each line in `swe.Dockerfile` does:

1. **Base Image**: Start from the latest version of the Ubuntu image.
```bash
FROM ubuntu:latest
```
2. **Build Argument**: Define a build argument `MINICONDA_URL` that will be used to specify the Miniconda installer URL during the build process.
```bash
ARG MINICONDA_URL
```
3. **Install Third-Party Tools**: Update the package lists for the Ubuntu package manager and install several essential development tools. Clean up after the installation.
```bash
RUN apt-get update && \
    apt-get install -y bash gcc git jq wget g++ make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```
4. **Initialize Git**: Configure global Git settings with a user email and name.
```bash
RUN git config --global user.email "sweagent@pnlp.org"
RUN git config --global user.name "sweagent"
```
5. **Environment Variables**: Set the `ROOT` environment variable and customize the shell prompt.
```bash
ENV ROOT='/dev/'
RUN prompt() { echo " > "; };
ENV PS1="> "
```
6. **Create Assets for Inference**: Create two files that are used to track metadata during an episode.
```bash
RUN touch /root/files_to_edit.txt
RUN touch /root/test.patch
```
7. **Enhance `ls` Command**: Modify the `.bashrc` file to alias the `ls` command.
```bash
RUN echo "alias ls='ls -F'" >> /root/.bashrc
```
8. Install Miniconda: Download and install Miniconda, then initialize conda with Bash support and add `conda-forge` to the channels list.
```bash
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN wget ${MINICONDA_URL} -O miniconda.sh \
    && mkdir /root/.conda \
    && bash miniconda.sh -b \
    && rm -f miniconda.sh
RUN conda --version \
    && conda init bash \
    && conda config --append channels conda-forge
```
9. **Install Python Packages**: Copy the `requirements.txt` file into the image and install the specified Python packages.
```bash
COPY docker/requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt
```
10. **Set Working Directory**: Set the working directory to the root directory.
```bash
WORKDIR /
```
11. **Default Command**: Set the default command to open a Bash shell when the container starts.
```bash
CMD ["/bin/bash"]
```