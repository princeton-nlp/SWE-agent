FROM --platform=linux/x86_64 python:3.11.10-bullseye

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

WORKDIR /

RUN mkdir -p /root/tools/defaults/lib
COPY tools/defaults/ /root/tools/defaults/
RUN touch /root/tools/defaults/lib/utils.sh

RUN pip install pipx
RUN pipx ensurepath
