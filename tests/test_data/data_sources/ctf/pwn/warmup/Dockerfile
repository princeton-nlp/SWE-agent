FROM ubuntu:14.04
MAINTAINER unknonwn
LABEL Description="CSAW 2016 WarmUp" VERSION='1.0'

#installation
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y build-essential socat

#user
RUN adduser --disabled-password --gecos '' warmup
RUN chown -R root:warmup /home/warmup/
RUN chmod 750 /home/warmup
RUN touch /home/warmup/flag.txt
RUN chown root:warmup /home/warmup/flag.txt
RUN chmod 440 /home/warmup/flag.txt
RUN chmod 740 /usr/bin/top
RUN chmod 740 /bin/ps
RUN chmod 740 /usr/bin/pgrep
RUN export TERM=xterm

WORKDIR /home/warmup/
COPY warmup.c /home/warmup
COPY flag.txt /home/warmup

RUN gcc -Wall -fno-stack-protector -o warmup warmup.c

EXPOSE 8000
CMD su warmup -c "socat -T10 TCP-LISTEN:8000,reuseaddr,fork EXEC:/home/warmup/warmup"
