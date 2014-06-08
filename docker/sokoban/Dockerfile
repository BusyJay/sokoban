# sphinx docs builder
# by jay

# version 0.2

FROM ubuntu:13.04

MAINTAINER Jay Lee <busyjaylee@gmail.com>

RUN echo "deb http://archive.ubuntu.com/ubuntu raring main universe" > /etc/apt/sources.list
RUN apt-get update
RUN apt-get upgrade -y

# user specific
RUN useradd -d /var/lib/sokoban -m -u 148 -r -c "Documentation synchonization tools" -s /bin/nologin sokoban
ENV HOME /var/lib/sokoban

# python develop environment
# we are not using python3-pip, because it will not be copied to virtual environment later.
RUN apt-get install -y build-essential
RUN apt-get install -y python-dev
RUN apt-get install -y python-pip
RUN apt-get install -y python-virtualenv
RUN apt-get install -y curl

# virtual environment
RUN sudo -u sokoban sh -c 'virtualenv ~/pyvenv2'
RUN sudo -u sokoban sh -c 'python3 -m venv ~/pyvenv3'
RUN sudo -u sokoban bash -c 'source ~/pyvenv2/bin/activate; \
pip install sphinx; \
deactivate; \
source ~/pyvenv3/bin/activate; \
curl -s https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python; \
pip install sphinx; \
deactivate'
# add seems not take the environment as run
ADD ./build.sh $HOME/build.sh
RUN chmod a+x ~/build.sh

# limit network access
# no elegant way to finish this with current docker version (0.9)

USER sokoban
WORKDIR /mnt
ENTRYPOINT ["/var/lib/sokoban/build.sh"]

