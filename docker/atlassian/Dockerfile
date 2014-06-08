# atlassian plugin docs builder
# by jay

# version 0.1

FROM ubuntu:13.04

MAINTAINER Jay Lee <busyjaylee@gmail.com>

# normal ubuntu update
RUN echo "deb http://archive.ubuntu.com/ubuntu raring main universe" > /etc/apt/sources.list
RUN apt-get update
RUN apt-get upgrade -y

# install jdk 6
RUN apt-get install -y curl
RUN curl -k -L -H "Cookie: oraclelicense=accept-securebackup-cookie" "http://download.oracle.com/otn-pub/java/jdk/6u45-b06/jdk-6u45-linux-x64.bin" -o /usr/local/jdk-6u45-linux-x64.bin
RUN cd /usr/local/; chmod a+x ./jdk-6u45-linux-x64.bin; ./jdk-6u45-linux-x64.bin
ENV JAVA_HOME /usr/local/jdk1.6.0_45
ENV PATH $JAVA_HOME/bin:$PATH

# install plugin sdk
RUN apt-get install -y apt-transport-https
RUN echo "deb https://sdkrepo.atlassian.com/debian/ stable contrib" >> /etc/apt/sources.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys B07804338C015B73
RUN apt-get update
RUN apt-get install -y atlassian-plugin-sdk

# config confluence
WORKDIR /srv
# cached concluence
RUN echo "n" | atlas-run-standalone --product confluence --version 5.3 --context-path ROOT 

CMD ["--product", "confluence", "--version", "5.3", "--context-path", "ROOT", "--server", "0.0.0.0"]
ENTRYPOINT ["/usr/bin/atlas-run-standalone"]
EXPOSE 1990


