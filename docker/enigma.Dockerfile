FROM sweagent/swe-agent:0.6.1

ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    build-essential \
    vim \
    cmake \
    libgtk2.0-dev \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libssl-dev \
    libffi-dev \
    libtbb2 \
    libtbb-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    ubuntu-desktop \
    bc \
    bsdmainutils \
    tshark \
    openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

# Install radare2
WORKDIR /tmp
RUN apt-get update && apt-get install -y curl netcat qemu-user qemu-user-static
RUN curl -LO https://github.com/radareorg/radare2/releases/download/5.9.4/radare2_5.9.4_amd64.deb
RUN dpkg -i radare2_5.9.4_amd64.deb

# Sagemath
RUN apt-get update && apt-get install -y sagemath

# sqlmap and nikto
RUN apt-get install -y sqlmap nikto

# Install apktool and jadx
RUN apt-get install -y apktool
RUN wget https://github.com/skylot/jadx/releases/download/v1.4.7/jadx-1.4.7.zip
RUN unzip -d /usr/local jadx-1.4.7.zip
RUN rm -f jadx-1.4.7.zip

# Install wine & wine32
RUN dpkg --add-architecture i386 && apt update && apt install -y wine wine32

# Install ghidra
RUN cd /opt \
    && wget -O ghidra.zip https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.0.1_build/ghidra_11.0.1_PUBLIC_20240130.zip \
    && unzip ghidra.zip \
    && rm -f ghidra.zip
ENV PATH=$PATH:/opt/ghidra_11.0.1_PUBLIC/support:/opt/ghidra_11.0.1_PUBLIC/Ghidra
COPY docker/ghidra_scripts /ghidra_scripts

# Install python requirements
ENV PIP_NO_CACHE_DIR=1
RUN pip install --upgrade pip
COPY docker/ctf_requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt && rm -f /root/requirements.txt

RUN cd /opt && git clone https://github.com/RsaCtfTool/RsaCtfTool.git && apt-get install -y libgmp3-dev libmpc-dev && cd RsaCtfTool && pip3 install -r "requirements.txt"
COPY docker/number_theory__fixed /opt/RsaCtfTool/lib/number_theory.py
ENV PATH=$PATH:/opt/RsaCtfTool
ENV PYTHONUNBUFFERED=1
ENV PWNLIB_NOTERM=1

# Install binwalk
RUN apt-get update && apt-get install -y binwalk

# Install sudo just in case the model still uses it
RUN apt-get install -y sudo

WORKDIR /

CMD ["/bin/bash"]