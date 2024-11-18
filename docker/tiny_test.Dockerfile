FROM alpine:latest

WORKDIR /

RUN mkdir -p /root/tools/defaults/lib
COPY tools/defaults/ /root/tools/defaults/
RUN touch /root/tools/defaults/lib/utils.sh
