FROM quay.io/pypa/manylinux2014_x86_64

RUN mkdir /home/nuitka
WORKDIR /home/nuitka

# Remove pypa manylinux python installations (but keep the cacert.pem file)
RUN echo 'Removing pypa manylinux python installations and unsetting the certificate it configured' && \
    yum reinstall -y ca-certificates && \
    rm -rf /opt/python /opt/_internal /build_scripts

# We need this to restore the SSL certificate configuration of pypa manylinux
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt

WORKDIR /home/nuitka

# Entry point
CMD ["/bin/bash"]
