#!/bin/bash

set -e
set -x

# The dependencies must be outside of the build folder because
# the python build process ends up running a find -delete that
# happens to also delete all the static libraries that we built.
export "PREFIX=$(pwd)/../Nuitka-Python-Deps"
export "CFLAGS=-mmacosx-version-min=10.9 -I${PREFIX}/include"
export "LDFLAGS=-L${PREFIX}/lib"
export "MACOSX_DEPLOYMENT_TARGET=10.9"


mkdir -p dep-build
cd dep-build

if [ ! -d readline-8.1 ]; then
curl https://ftp.gnu.org/gnu/readline/readline-8.1.tar.gz -o readline.tar.gz
tar -xf readline.tar.gz
cd readline-8.1
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d ncurses-6.3 ]; then
curl https://ftp.gnu.org/gnu/ncurses/ncurses-6.3.tar.gz -o ncurses.tar.gz
tar -xf ncurses.tar.gz
cd ncurses-6.3
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d sqlite-autoconf-3390200 ]; then
curl https://sqlite.org/2022/sqlite-autoconf-3390200.tar.gz -o sqlite.tar.gz
tar -xf sqlite.tar.gz
cd sqlite-autoconf-3390200
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d openssl-1.1.1q ]; then
curl https://www.openssl.org/source/openssl-1.1.1q.tar.gz -o openssl.tar.gz
tar -xf openssl.tar.gz
cd openssl-1.1.1q
./configure --prefix=${PREFIX} darwin64-x86_64-cc enable-ec_nistp_64_gcc_128 no-shared no-tests
make depend all -j$(sysctl -n hw.ncpu)
make install 
cd ..
fi

if [ ! -d gdbm-1.23 ]; then
curl https://ftp.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz -o gdbm.tar.gz
tar -xf gdbm.tar.gz
cd gdbm-1.23
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d bzip2-1.0.8 ]; then
curl https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz -o bzip2.tar.gz
tar -xf bzip2.tar.gz
cd bzip2-1.0.8
make install "PREFIX=$PREFIX" CFLAGS=-mmacosx-version-min=10.9 LDFLAGS=-mmacosx-version-min=10.9 -j$(sysctl -n hw.ncpu)
cd ..
fi

if [ ! -d util-linux-2.38 ]; then
curl https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.38/util-linux-2.38.tar.gz -o util-linux.tar.gz
tar -xf util-linux.tar.gz
cd util-linux-2.38
./configure --prefix=${PREFIX} --disable-shared --disable-all-programs --enable-libuuid
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d xz-5.2.5 ]; then
curl -L https://downloads.sourceforge.net/project/lzmautils/xz-5.2.5.tar.gz -o xz.tar.gz
tar -xf xz.tar.gz
cd xz-5.2.5
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d libffi-3.4.2 ]; then
curl -L https://github.com/libffi/libffi/releases/download/v3.4.2/libffi-3.4.2.tar.gz -o libffi.tar.gz
tar -xf libffi.tar.gz
cd libffi-3.4.2
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d zlib-1.2.12 ]; then
curl -L https://zlib.net/zlib-1.2.12.tar.gz -o zlib.tar.gz
tar -xf zlib.tar.gz
cd zlib-1.2.12
./configure --prefix=${PREFIX} --static
make -j$(sysctl -n hw.ncpu)
make install
cd ..   
fi

if [ ! -d libiconv-1.17 ]; then
curl https://ftp.gnu.org/pub/gnu/libiconv/libiconv-1.17.tar.gz -o iconv.tar.gz
tar -xf iconv.tar.gz
cd libiconv-1.17
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

if [ ! -d gettext-0.21 ]; then
curl https://ftp.gnu.org/pub/gnu/gettext/gettext-0.21.tar.gz -o gettext.tar.gz
tar -xf gettext.tar.gz
cd gettext-0.21
./configure --prefix=${PREFIX} --disable-shared
make -j$(sysctl -n hw.ncpu)
make install
cd ..
fi

cd ..



long_version=$(git branch --show-current 2>/dev/null || git symbolic-ref --short HEAD)
short_version=$(echo $long_version | sed -e 's#\.##')

# Have this as a standard path. We are not yet relocatable, but that will come hopefully.
target=~/Library/Nuitka-Python${short_version}

if [ ! -z "$1" ]
then
  target="$1"
fi

# Allow to overload the compiler used via CC environment variable
if [ "$CC" = "" ]
then
  export CC=clang
  export CXX=clang++
else
  export CXX=`echo "$CC" | sed -e 's#cc#++#'`
fi

export CC
export CXX

ELEVATE=
if [ ! -w "$(dirname "$target")" ]
then
  export "ELEVATE=sudo --preserve-env=CC,CXX"
  $ELEVATE echo
fi

cp Modules/Setup.macos Modules/Setup

# The UCS4 has best compatibility with wheels on PyPI it seems.
./configure "--prefix=$target" --disable-shared --enable-ipv6 --enable-unicode=ucs4 \
  --enable-optimizations --with-lto --with-computed-gotos --with-fpectl \
  CC="$CC" \
  CXX="$CXX" \
  CFLAGS="-g -mmacosx-version-min=10.9 $CFLAGS" \
  LDFLAGS="-g -Xlinker $LDFLAGS" \
  LIBS="-lffi -lbz2 -luuid -lsqlite3 -llzma"

make -j 32 \
        EXTRA_CFLAGS="-flto" \
        PROFILE_TASK='./Lib/test/regrtest.py -j 8 -x test_bsddb3 test_compiler test_cpickle test_cprofile test_dbm_dumb test_dbm_ndbm test_distutils test_ensurepip test_gdb test_io test_linuxaudiodev test_multiprocessing test_ossaudiodev test_platform test_pydoc test_socketserver test_subprocess test_sundry test_thread test_threaded_import test_threadedtempfile test_threading test_threading_local test_threadsignals test_xmlrpc test_zipfile' \
        profile-opt

make build_all_merge_profile

# Delayed deletion of old installation, to avoid having it not there for testing purposes
# while compiling, which is slow due to PGO beign applied.
$ELEVATE rm -rf "$target" && $ELEVATE make install

# Make sure to have pip installed, might even remove it afterwards, Debian
# e.g. doesn't include it.
$ELEVATE mv "$target/lib/python${long_version}/pip.py" "$target/lib/python${long_version}/pip.py.bak" && \
    $ELEVATE "$target/bin/python${long_version}" -m ensurepip && \
    $ELEVATE "$target/bin/python${long_version}" install_ssl.py && \
    $ELEVATE mv "$target/lib/python${long_version}/pip.py.bak" "$target/lib/python${long_version}/pip.py"

# Copy over the compiled dependencies.
$ELEVATE mkdir -p "$target/dependency_libs"
$ELEVATE cp -r "$(pwd)/../Nuitka-Python-Deps" "$target/dependency_libs/base"
$ELEVATE ln -s base "$target/dependency_libs/readline"
$ELEVATE ln -s base "$target/dependency_libs/ncurses"
$ELEVATE ln -s base "$target/dependency_libs/sqlite"
$ELEVATE ln -s base "$target/dependency_libs/openssl"
$ELEVATE ln -s base "$target/dependency_libs/gdbm"
$ELEVATE ln -s base "$target/dependency_libs/bzip2"
$ELEVATE ln -s base "$target/dependency_libs/uuid"
$ELEVATE ln -s base "$target/dependency_libs/xz"
$ELEVATE ln -s base "$target/dependency_libs/ffi"
$ELEVATE ln -s base "$target/dependency_libs/zlib"
$ELEVATE ln -s base "$target/dependency_libs/iconv"
$ELEVATE ln -s base "$target/dependency_libs/gettext"

$ELEVATE "$target/bin/python${long_version}" -m rebuildpython

