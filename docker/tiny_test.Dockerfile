FROM python:3.11.10-bullseye

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

WORKDIR /

RUN pip install pipx
RUN pipx ensurepath
RUN pipx install 0fdb5604
