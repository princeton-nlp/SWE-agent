FROM sweagent/swe-agent:0.6.1

# Set up target architecture and non-interactive frontend
ARG TARGETARCH
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 PWNLIB_NOTERM=1

# Install core packages and libraries, remove apt cache afterward
RUN apt-get update && apt-get install -y \
    build-essential vim cmake libgtk2.0-dev pkg-config libavcodec-dev \
    libavformat-dev libswscale-dev libssl-dev libffi-dev libtbb2 libtbb-dev \
    libjpeg-dev libpng-dev libtiff-dev ubuntu-desktop bc bsdmainutils tshark \
    openjdk-17-jdk curl netcat qemu-user qemu-user-static sqlmap nikto sagemath \
    apktool wine wine32 binwalk sudo && \
    rm -rf /var/lib/apt/lists/*

# Install radare2
WORKDIR /tmp
RUN curl -LO https://github.com/radareorg/radare2/releases/download/5.9.4/radare2_5.9.4_amd64.deb && \
    dpkg -i radare2_5.9.4_amd64.deb && \
    rm -f radare2_5.9.4_amd64.deb

# Install jadx
RUN wget -q https://github.com/skylot/jadx/releases/download/v1.4.7/jadx-1.4.7.zip && \
    unzip -q -d /usr/local jadx-1.4.7.zip && \
    rm -f jadx-1.4.7.zip

# Install Ghidra
RUN cd /opt && \
    wget -q -O ghidra.zip https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.0.1_build/ghidra_11.0.1_PUBLIC_20240130.zip && \
    unzip -q ghidra.zip && \
    rm -f ghidra.zip
ENV PATH=$PATH:/opt/ghidra_11.0.1_PUBLIC/support:/opt/ghidra_11.0.1_PUBLIC/Ghidra

# Copy Ghidra scripts
COPY docker/ghidra_scripts /ghidra_scripts

# Install Python dependencies
RUN pip install --upgrade pip
COPY docker/ctf_requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt && rm -f /root/requirements.txt

# Install RsaCtfTool and its dependencies
RUN cd /opt && \
    git clone https://github.com/RsaCtfTool/RsaCtfTool.git && \
    apt-get update && apt-get install -y libgmp3-dev libmpc-dev && \
    cd RsaCtfTool && pip3 install -r "requirements.txt"
COPY docker/number_theory__fixed /opt/RsaCtfTool/lib/number_theory.py
ENV PATH=$PATH:/opt/RsaCtfTool

# Clean up and set working directory
WORKDIR /
CMD ["/bin/bash"]
