#!/bin/bash

set -x


# Install Debian dependencies.
# TODO: Support Fedora/CentOS/etc. as well.
if command -v apt &> /dev/null
then
  pkgs='build-essential libc6-dev'
  install=false
  for pkg in $pkgs; do
    status="$(dpkg-query -W --showformat='${db:Status-Status}' "$pkg" 2>&1)"
    if [ ! $? = 0 ] || [ ! "$status" = installed ]; then
      install=true
      break
    fi
  done
  if "$install"; then
    sudo apt install $pkgs
  fi
fi

set -e
set -x

# The dependencies must be outside of the build folder because
# the python build process ends up running a find -delete that
# happens to also delete all the static libraries that we built.
export "PREFIX=$(pwd)/../Nuitka-Python-Deps"
export "CFLAGS=-I${PREFIX}/include"
export "LDFLAGS=-L${PREFIX}/lib"
export "PKG_CONFIG_PATH=${PREFIX}/lib/pkgconfig"

mkdir -p dep-build
cd dep-build

if [ ! -d readline-8.2 ]; then
curl https://ftp.gnu.org/gnu/readline/readline-8.2.tar.gz -o readline.tar.gz
tar -xf readline.tar.gz
cd readline-8.2
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d ncurses-6.4 ]; then
curl https://ftp.gnu.org/gnu/ncurses/ncurses-6.4.tar.gz -o ncurses.tar.gz
tar -xf ncurses.tar.gz
cd ncurses-6.4
./configure --prefix=${PREFIX} --disable-shared --enable-termcap --enable-widec --enable-getcap
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d sqlite-autoconf-3440000 ]; then
curl https://sqlite.org/2023/sqlite-autoconf-3440000.tar.gz -o sqlite.tar.gz
tar -xf sqlite.tar.gz
cd sqlite-autoconf-3440000
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d openssl-3.1.4 ]; then
curl https://www.openssl.org/source/openssl-3.1.4.tar.gz -o openssl.tar.gz
tar -xf openssl.tar.gz
cd openssl-3.1.4
./Configure --prefix=${PREFIX} --libdir=lib linux-x86_64 enable-ec_nistp_64_gcc_128 no-shared no-tests
make depend all -j$(nproc --all)
make install
cd ..
fi

if [ ! -d gdbm-1.23 ]; then
curl https://ftp.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz -o gdbm.tar.gz
tar -xf gdbm.tar.gz
cd gdbm-1.23
./configure --prefix=${PREFIX} --disable-shared --enable-libgdbm-compat
make -j$(nproc --all)
make install
mkdir -p ${PREFIX}/include/gdbm
cp ./compat/dbm.h ./compat/ndbm.h ${PREFIX}/include/gdbm
cd ..
fi

if [ ! -d bzip2-1.0.8 ]; then
curl https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz -o bzip2.tar.gz
tar -xf bzip2.tar.gz
cd bzip2-1.0.8
make install "PREFIX=$PREFIX" -j$(nproc --all)
cd ..
fi

if [ ! -d util-linux-2.39 ]; then
curl https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.39/util-linux-2.39.tar.gz -o util-linux.tar.gz
tar -xf util-linux.tar.gz
cd util-linux-2.39
./configure --prefix=${PREFIX} --disable-shared --disable-all-programs --enable-libuuid
make -j$(nproc --all)
make install
cp ./libuuid/src/uuid.h ${PREFIX}/include/
cd ..
fi

if [ ! -d xz-5.4.5 ]; then
curl -L https://downloads.sourceforge.net/project/lzmautils/xz-5.4.5.tar.gz -o xz.tar.gz
tar -xf xz.tar.gz
cd xz-5.4.5
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libffi-3.4.4 ]; then
curl -L https://github.com/libffi/libffi/releases/download/v3.4.4/libffi-3.4.4.tar.gz -o libffi.tar.gz
tar -xf libffi.tar.gz
cd libffi-3.4.4
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d zlib-latest ]; then
curl -L https://www.zlib.net/current/zlib.tar.gz -o zlib.tar.gz
tar -xf zlib.tar.gz
mv zlib-* zlib-latest
cd zlib-latest
./configure --prefix=${PREFIX} --static
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libiconv-1.17 ]; then
curl https://ftp.gnu.org/pub/gnu/libiconv/libiconv-1.17.tar.gz -o iconv.tar.gz
tar -xf iconv.tar.gz
cd libiconv-1.17
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d gettext-0.22.3 ]; then
curl https://ftp.gnu.org/pub/gnu/gettext/gettext-0.22.3.tar.gz -o gettext.tar.gz
tar -xf gettext.tar.gz
cd gettext-0.22.3
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libxcrypt-4.4.36 ]; then
curl -L https://github.com/besser82/libxcrypt/releases/download/v4.4.36/libxcrypt-4.4.36.tar.xz -o libxcrypt.tar.xz
tar -xf libxcrypt.tar.xz
cd libxcrypt-4.4.36
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d bzip2-bzip2-1.0.8 ]; then
curl https://gitlab.com/bzip2/bzip2/-/archive/bzip2-1.0.8/bzip2-bzip2-1.0.8.tar.gz -o bzip2.tar.gz
tar -xf bzip2.tar.gz
cd bzip2-bzip2-1.0.8
make -j$(nproc --all)
make install PREFIX=${PREFIX}
cd ..
fi

if [ ! -d libffi-3.4.4 ]; then
curl -L https://github.com/libffi/libffi/releases/download/v3.4.4/libffi-3.4.4.tar.gz -o libffi.tar.gz
tar -xf libffi.tar.gz
cd libffi-3.4.4
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libpng-1.6.39 ]; then
curl -L http://downloads.sourceforge.net/project/libpng/libpng16/1.6.39/libpng-1.6.39.tar.xz -o libpng.tar.gz
tar -xf libpng.tar.gz
cd libpng-1.6.39
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d harfbuzz-8.3.0 ]; then
curl -L https://github.com/harfbuzz/harfbuzz/releases/download/8.3.0/harfbuzz-8.3.0.tar.xz -o harfbuzz.tar.gz
tar -xf harfbuzz.tar.gz
cd harfbuzz-8.3.0
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d tcl8.6.13 ]; then
curl -L http://downloads.sourceforge.net/project/tcl/Tcl/8.6.13/tcl8.6.13-src.tar.gz -o tcl.tar.gz
tar -xf tcl.tar.gz
cd tcl8.6.13/unix
./configure --prefix=${PREFIX} --enable-shared=no --enable-threads
make -j$(nproc --all)
make install
cd ../..
fi

if [ ! -d tk8.6.13 ]; then
curl -L http://downloads.sourceforge.net/project/tcl/Tcl/8.6.13/tk8.6.13-src.tar.gz -o tk.tar.gz
tar -xf tk.tar.gz
cd tk8.6.13/unix
./configure --prefix=${PREFIX} --enable-shared=no --enable-threads --with-tcl=${PREFIX}/lib
make -j$(nproc --all)
make install
cd ../..
fi

if [ ! -d xtrans-1.5.0 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/xtrans-1.5.0.tar.gz -o xtrans.tar.gz
tar -xf xtrans.tar.gz
cd xtrans-1.5.0
./configure --prefix=${PREFIX} --datarootdir=${PREFIX}/lib
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libX11-1.8.7 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libX11-1.8.7.tar.gz -o libX11.tar.gz
tar -xf libX11.tar.gz
cd libX11-1.8.7
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXScrnSaver-1.2.4 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXScrnSaver-1.2.4.tar.gz -o libXScrnSaver.tar.gz
tar -xf libXScrnSaver.tar.gz
cd libXScrnSaver-1.2.4
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXft-2.3.8 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXft-2.3.8.tar.gz -o libXft.tar.gz
tar -xf libXft.tar.gz
cd libXft-2.3.8
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libxcb-1.16 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libxcb-1.16.tar.gz -o libxcb.tar.gz
tar -xf libxcb.tar.gz
cd libxcb-1.16
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXext-1.3.5 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXext-1.3.5.tar.gz -o libXext.tar.gz
tar -xf libXext.tar.gz
cd libXext-1.3.5
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXdmcp-1.1.4 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXdmcp-1.1.4.tar.gz -o libXdmcp.tar.gz
tar -xf libXdmcp.tar.gz
cd libXdmcp-1.1.4
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXrandr-1.5.4 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXrandr-1.5.4.tar.gz -o libXrandr.tar.gz
tar -xf libXrandr.tar.gz
cd libXrandr-1.5.4
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXau-1.0.11 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXau-1.0.11.tar.gz -o libXau.tar.gz
tar -xf libXau.tar.gz
cd libXau-1.0.11
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libXrender-0.9.11 ]; then
curl -L https://xorg.freedesktop.org/releases/individual/lib/libXrender-0.9.11.tar.gz -o libXrender.tar.gz
tar -xf libXrender.tar.gz
cd libXrender-0.9.11
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d fontconfig-2.15.0 ]; then
curl -L https://www.freedesktop.org/software/fontconfig/release/fontconfig-2.15.0.tar.gz -o fontconfig.tar.gz
tar -xf fontconfig.tar.gz
cd fontconfig-2.15.0
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d freetype-2.13.2 ]; then
curl -L https://download.savannah.gnu.org/releases/freetype/freetype-2.13.2.tar.gz -o freetype.tar.gz
tar -xf freetype.tar.gz
cd freetype-2.13.2
./configure --prefix=${PREFIX} --disable-shared --with-brotli=no
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d expat-2.5.0 ]; then
curl -L https://github.com/libexpat/libexpat/releases/download/R_2_5_0/expat-2.5.0.tar.gz -o expat.tar.gz
tar -xf expat.tar.gz
cd expat-2.5.0
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

if [ ! -d libb2-0.98.1 ]; then
curl -L https://github.com/BLAKE2/libb2/releases/download/v0.98.1/libb2-0.98.1.tar.gz -o libb2.tar.gz
tar -xf libb2.tar.gz
cd libb2-0.98.1
./configure --prefix=${PREFIX} --disable-shared
make -j$(nproc --all)
make install
cd ..
fi

cd ..

long_version=$(git branch --show-current 2>/dev/null || git symbolic-ref --short HEAD)
short_version=$(echo $long_version | sed -e 's#\.##')

# Have this as a standard path. We are not yet relocatable, but that will come hopefully.
target=/opt/nuitka-python${short_version}

if [ ! -z "$1" ]
then
  target="$1"
fi

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

ELEVATE=
if [ ! -w "$(dirname "$target")" ]
then
  export "ELEVATE=sudo \"CC=$CC\" \"CXX=$CXX\""
  sudo echo
fi

# The UCS4 has best compatibility with wheels on PyPI it seems.
./configure "--prefix=$target" --disable-shared --enable-ipv6 --enable-unicode=ucs4 \
  --enable-optimizations --with-lto --with-computed-gotos --with-fpectl \
  CC="$CC" \
  CXX="$CXX" \
  CFLAGS="-g $CFLAGS" \
  LDFLAGS="-g -Xlinker -export-dynamic -rdynamic -Bsymbolic-functions -Wl,-z,relro -Wl,-allow-multiple-definition $LDFLAGS" \
  LIBS="-l:libffi.a -l:libbz2.a -l:libuuid.a -l:libsqlite3.a -l:liblzma.a -l:librt.a"

make -j 32 \
        EXTRA_CFLAGS="-flto -fuse-linker-plugin -fno-fat-lto-objects" \
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


$ELEVATE mkdir -p "$target/dependency_libs"
$ELEVATE cp -r "$(pwd)/../Nuitka-Python-Deps" "$target/dependency_libs/base"
$ELEVATE ln -s base "$target/dependency_libs/bzip2"
$ELEVATE ln -s base "$target/dependency_libs/expat"
$ELEVATE ln -s base "$target/dependency_libs/fontconfig"
$ELEVATE ln -s base "$target/dependency_libs/freetype"
$ELEVATE ln -s base "$target/dependency_libs/gdbm"
$ELEVATE ln -s base "$target/dependency_libs/gettext"
$ELEVATE ln -s base "$target/dependency_libs/harfbuzz"
$ELEVATE ln -s base "$target/dependency_libs/b2"
$ELEVATE ln -s base "$target/dependency_libs/ffi"
$ELEVATE ln -s base "$target/dependency_libs/iconv"
$ELEVATE ln -s base "$target/dependency_libs/png"
$ELEVATE ln -s base "$target/dependency_libs/X11"
$ELEVATE ln -s base "$target/dependency_libs/xcb"
$ELEVATE ln -s base "$target/dependency_libs/xcrypt"
$ELEVATE ln -s base "$target/dependency_libs/ncurses"
$ELEVATE ln -s base "$target/dependency_libs/openssl"
$ELEVATE ln -s base "$target/dependency_libs/readline"
$ELEVATE ln -s base "$target/dependency_libs/sqlite"
$ELEVATE ln -s base "$target/dependency_libs/tcltk"
$ELEVATE ln -s base "$target/dependency_libs/uuid"
$ELEVATE ln -s base "$target/dependency_libs/xtrans"
$ELEVATE ln -s base "$target/dependency_libs/xz"
$ELEVATE ln -s base "$target/dependency_libs/zlib"


$ELEVATE "$target/bin/python${long_version}" -m rebuildpython
