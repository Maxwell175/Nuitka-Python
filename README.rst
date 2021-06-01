This is Nuitka-Python
=====================

This is a fork of CPython, that is not called CPython, but Nuitka-Python and diverges
in various ways.

Our immediate goals are:

* Windows: Add static linking (performance and lock down).
* Windows: Reenable Windows 7 support (because why not).
* LTO linking on Windows (performance and deployment size)

Installation
============

Currently, you have to build this from source code. It is questionable if deploying
binaries makes sense, as you will have to compile from source code everything else
that is installed, and the ``python.exe`` will be self-modifying with pip installs.

Use the following command in the root of a Nuitka-Python checkout:

.. code:: sh

    PCbuild\build.bat -e -p x64

This produces a Python install in the ``PCbuild/amd64/python`` folder. This doesn't
have pip, but you add it with the following command:

.. code:: sh

    PCbuild\amd64\python -m ensurepip

This will download and install pip and setuptools. Nuitka-Python supports these with
differences to standard CPython that make it essentially always compile from source.

Copyright and License Information
---------------------------------

Copyright (c) 2021 Nuitka Organsisation contributors. All rights reserved.

Copyright (c) 2001-2021 Python Software Foundation.  All rights reserved.

Copyright (c) 2000 BeOpen.com.  All rights reserved.

Copyright (c) 1995-2001 Corporation for National Research Initiatives.  All
rights reserved.

Copyright (c) 1991-1995 Stichting Mathematisch Centrum.  All rights reserved.

See the file "LICENSE" for information on the history of this software, terms &
conditions for usage, and a DISCLAIMER OF ALL WARRANTIES.

This Python distribution contains *no* GNU General Public License (GPL) code,
so it may be used in proprietary projects.  There are interfaces to some GNU
code but these are entirely optional.

All trademarks referenced herein are property of their respective holders.
