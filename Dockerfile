FROM artprod.dev.bloomberg.com/dpkg-python-development-base:3.7


RUN apt-get install -y \
    bash \
    bash-completion \
    git \
    vim \
    rsync

#RUN apt-get install -y

RUN python3.7 -m pip install --upgrade pip &&  \
    python3.7 -m pip install \
    pudb \
    debugpy


