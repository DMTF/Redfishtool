FROM ubuntu:latest
MAINTAINER Randeep Jalli <jallirs@gmail.com>

RUN set -ex ;\
    apt-get update ;\
    apt-get upgrade -y ;\
    apt-get install -y \
      python \
      virtualenv \
      python-dev \
      gcc \
      git
      
COPY install-redfishtool.sh /usr/local/bin/install-python-packages.sh

RUN chmod a+x /usr/local/bin/install-python-packages.sh
RUN /usr/local/bin/install-python-packages.sh git+https://github.com/DMTF/Redfishtool.git

ENV PATH=/var/lib/redfishtool-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

      
