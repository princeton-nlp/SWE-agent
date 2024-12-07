FROM ubuntu:jammy

ARG TARGETARCH

# Install third party tools
RUN apt-get update && \
    apt-get install -y bash gcc git jq wget g++ make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Initialize git
RUN git config --global user.email "sweagent@pnlp.org"
RUN git config --global user.name "sweagent"

# Environment variables
ENV ROOT='/dev/'
RUN prompt() { echo " > "; };
ENV PS1="> "

# Create file for tracking edits, test patch
RUN touch /root/files_to_edit.txt
RUN touch /root/test.patch

# add ls file indicator
RUN echo "alias ls='ls -F'" >> /root/.bashrc

# Install miniconda
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
COPY SWE-agent/docker/getconda.sh .
RUN bash getconda.sh ${TARGETARCH} \
    && rm getconda.sh \
    && mkdir /root/.conda \
    && bash miniconda.sh -b \
    && rm -f miniconda.sh
RUN conda --version \
    && conda init bash \
    && conda config --append channels conda-forge

# Cache python versions
RUN conda create -y -n python3.9 python=3.9
RUN conda create -y -n python3.10 python=3.10

# Install python packages
COPY SWE-agent/docker/requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt

RUN mkdir /root/swe-rex
COPY swe-rex /root/swe-rex
RUN pip install -e /root/swe-rex

WORKDIR /

CMD ["/bin/bash"]
