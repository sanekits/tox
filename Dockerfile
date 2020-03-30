FROM alpine

WORKDIR /root
ENV SHELL /bin/bash
ENV USER root

RUN apk add \
    bash \
    bash-completion \
    git \
    python3

RUN python3.8 -m pip install --upgrade pip && python3.8 -m pip install pudb

WORKDIR /etc
RUN /bin/sed -i 's^/bin/ash^/bin/bash^' passwd

WORKDIR /app
COPY . .
RUN mkdir -p /root/bin ; ln -s /app /root/bin/tox-py

WORKDIR /root
COPY docker_bashrc_root .bashrc
RUN echo '. /root/.bashrc' >/root/.profile

RUN bash -l -c 'pwd && echo $BASH_VERSION'
