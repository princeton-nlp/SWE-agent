FROM python:3.11.10-bullseye

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

WORKDIR /

RUN pip install pipx
RUN pipx install 0fdb5604
RUN pip install flake8
RUN pipx ensurepath

SHELL ["/bin/bash", "-c"]
# This is where pipx installs things
ENV PATH="$PATH:/root/.local/bin/"
