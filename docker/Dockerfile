FROM quay.io/pypa/manylinux2014_x86_64

# 'Development Tools' group is the equivalent of 'build-essential' package in Ubuntu
RUN echo "Installing Development Tools"
RUN yum install -y perl-IPC-Cmd gperf git

WORKDIR /Nuitka-Python

# Entry point
CMD ["/bin/bash"]