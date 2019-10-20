FROM ubuntu:18.04

RUN apt update \
# install python3, pip and dependencies
    && apt install software-properties-common -y \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt update \
    && apt install python3.7 -y \
    && apt install python3-pip -y \
    # mtr is a tool for making async ICMP pings with mtrpacket module
    && apt install mtr -y

RUN mkdir /src
WORKDIR /src
ADD deploy/requirements.txt /src/

RUN python3.7 -m pip install -r requirements.txt
