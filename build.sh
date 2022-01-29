#!/bin/bash

exec >build-stdout.txt 2>build-stderr.txt

set -e
set -x

# Install Debian dependencies.
# TODO: Support Fedora/CentOS/etc. as well.
sudo apt-get update
sudo apt-get install -y build-essential checkinstall libreadline-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev

short_version=$(git branch --show-current | sed -e 's#\.##')
long_version=$(git branch --show-current)

# Have this as a standard path. We are not yet relocatable, but that will come hopefully.
target=/opt/nuitka-python${short_version}

# Allow to overload the compiler used via CC environment variable
if [ "$CC" = "" ]
then
  CC=gcc
  CXX=g++
else
  CXX=`echo "$CC" | sed -e 's#cc#++#'`
fi

export CC
export CXX

# The UCS4 has best compatibility with wheels on PyPI it seems.
./configure --prefix=$target --disable-shared --enable-ipv6 --enable-unicode=ucs4 \
  --enable-optimizations --with-lto --with-computed-gotos --with-fpectl \
  CC=$CC \
  CXX=$CXX \
  CFLAGS="-g" \
  LDFLAGS="-g -Xlinker -export-dynamic -rdynamic -Bsymbolic-functions -Wl,-z,relro" \
  LIBS="-lffi -lbz2 -luuid -lsqlite3 -llzma"

make -j 32 \
        EXTRA_CFLAGS="-flto -fuse-linker-plugin -ffat-lto-objects" \
        PROFILE_TASK='./Lib/test/regrtest.py -x test_bsddb3 test_compiler test_cpickle test_cprofile test_dbm_dumb test_dbm_ndbm test_distutils test_ensurepip test_gdb test_io test_linuxaudiodev test_multiprocessing test_ossaudiodev test_platform test_pydoc test_socketserver test_subprocess test_sundry test_thread test_threaded_import test_threadedtempfile test_threading test_threading_local test_threadsignals test_xmlrpc test_zipfile' \
        profile-opt

make build_all_merge_profile

# Delayed deletion of old installation, to avoid having it not there for testing purposes
# while compiling, which is slow due to PGO beign applied.
sudo rm -rf $target && sudo --preserve-env=CC,CXX make install

# Make sure to have pip installed, might even remove it afterwards, Debian
# e.g. doesn't include it.
sudo mv $target/lib/python${long_version}/pip.py $target/lib/python${long_version}/pip.py.bak && sudo $target/bin/python -m ensurepip && sudo mv $target/lib/python${long_version}/pip.py.bak $target/lib/python${long_version}/pip.py
