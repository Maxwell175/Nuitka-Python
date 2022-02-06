from __future__ import print_function

import ctypes
import distutils
import distutils.ccompiler
import fnmatch
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile

MOVEFILE_DELAY_UNTIL_REBOOT = 4


def find_files(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def getPythonInitFunctions(compiler, filename):
    if platform.system() == "Windows":
        initFunctions = [
            x.decode("ascii").split(" ")[-1]
            for x in subprocess.check_output(
                [compiler.dumpbin, "/linkermember", filename]
            ).split(b"\r\n")
            if (b"init" if str is bytes else b"PyInit_") in x
        ]
    else:
        functions = [
            x.decode("ascii").split(" ")[-1]
            for x in subprocess.check_output(["nm", filename]).split(
                os.linesep.encode("ascii")
            )
        ]
        initFunctions = [
            x for x in functions if x.startswith("init" if str is bytes else "PyInit_")
        ]

    initFunctions = [
        y for y in initFunctions if "$" not in y and "@" not in y and "?" not in y
    ]

    return initFunctions


def run_rebuild():
    installDir = os.path.dirname(sys.executable)

    has_compiler_vars = sysconfig.get_config_var("CC") and sysconfig.get_config_var("CXX")

    # Make sure we have the same compiler as used originally.
    if has_compiler_vars:
        cc_config_var = sysconfig.get_config_var("CC").split()[0]
        if "CC" in os.environ and os.environ["CC"] != cc_config_var:
            print("Overriding CC variable to Nuitka-Python used '%s' ..." % cc_config_var)
        os.environ["CC"] = cc_config_var

        cxx_config_var = sysconfig.get_config_var("CXX").split()[0]
        if "CXX" in os.environ and os.environ["CXX"] != cxx_config_var:
            print("Overriding CXX variable to Nuitka-Python used '%s' ..." % cxx_config_var)
        os.environ["CXX"] = cxx_config_var

    compiler = distutils.ccompiler.new_compiler(verbose=5)
    if has_compiler_vars:
        compiler.set_executables(
            compiler=cc_config_var,
            compiler_so=cc_config_var,
            linker_exe=cc_config_var,
            compiler_cxx=cxx_config_var,
        )

    try:
        compiler.initialize()
    except AttributeError:
        pass

    foundLibs = {}
    checkedLibs = set()

    from distutils.sysconfig import get_config_var

    ext_suffix = get_config_var("EXT_SUFFIX")

    extra_scan_dirs = []
    if platform.system() == "Windows":
        extra_scan_dirs.append(os.path.join(sysconfig.get_config_var('srcdir'), 'libs'))

    # Scan sys.path for any more lingering static libs.
    for path in list(reversed(sys.path)) + extra_scan_dirs:
        # Ignore the working directory so we don't grab duplicate stuff.
        if path == os.getcwd() or installDir == path or path in installDir:
            continue
        for file in find_files(
                path, "*.lib" if platform.system() == "Windows" else "*.a"
        ):
            if file in checkedLibs:
                continue

            filename_base = os.path.basename(file)

            python_lib = sysconfig.get_config_var("LIBRARY")
            if (platform.system() != "Windows" and not filename_base.startswith("lib")) or \
                    (python_lib is not None and filename_base.endswith(sysconfig.get_config_var("LIBRARY"))):
                continue

            checkedLibs.add(filename_base)

            initFunctions = getPythonInitFunctions(compiler, file)

            # If this lib has a Python init function, we should link it in.
            if initFunctions:
                relativePath = os.path.relpath(file, path)
                if "site-packages" in relativePath:
                    continue
                dirpath, filename = os.path.split(relativePath)
                if platform.system() != "Windows" and filename.startswith("lib"):
                    filename = filename[3:]
                if filename.endswith(".a"):
                    filename = filename[:-2]
                if filename.endswith(".lib"):
                    filename = filename[:-4]
                if ext_suffix and filename.endswith(ext_suffix):
                    filename = filename[: len(ext_suffix) * -1]
                relativePath = (
                        dirpath.replace("\\", ".").replace("/", ".") + "." + filename
                )
                print(relativePath, file)
                foundLibs[relativePath] = file

    print("Scanning for any additional libs to link...")

    # Start with the libs needed for a base interpreter.
    if platform.system() == "Windows":
        link_libs = [
            "advapi32",
            "shell32",
            "ole32",
            "oleaut32",
            "kernel32",
            "user32",
            "gdi32",
            "winspool",
            "comdlg32",
            "uuid",
            "odbc32",
            "odbccp32",
            "shlwapi",
            "ws2_32",
            "version",
            "libssl",
            "libcrypto",
            "tcl86t",
            "tk86t",
            "Crypt32",
            "Iphlpapi",
            "msi",
            "Rpcrt4",
            "Cabinet",
            "winmm",
        ]
    else:
        link_libs = ["m"]

    if platform.system() == "Windows":
        library_dirs = [
            sysconfig.get_config_var("srcdir"),
            os.path.join(sysconfig.get_config_var("srcdir"), "libs"),
            os.path.join(sysconfig.get_config_var("srcdir"), "tcl"),
        ]
    else:
        library_dirs = [
            sysconfig.get_config_var("prefix"),
            sysconfig.get_config_var("LIBDEST"),
            sysconfig.get_config_var("LIBDIR"),
        ]

    # Scrape all available libs from the libs directory. We will let the linker worry about filtering out extra symbols.
    for file in find_files(
            sysconfig.get_config_var("prefix"),
            "*.lib" if platform.system() == "Windows" else "*.a",
    ):
        link_libs.append(file)

    for _name, path in foundLibs.items():
        link_libs += [path]

        if os.path.isfile(path + ".link.json"):
            with open(path + ".link.json", "r") as f:
                linkData = json.load(f)
                link_libs += linkData["libraries"]
                library_dirs += [
                    os.path.join(os.path.dirname(path), x)
                    for x in linkData["library_dirs"]
                ]

    link_libs = list(set(link_libs))
    library_dirs = list(set(library_dirs))

    print("Generating interpreter sources...")

    staticinitheader = """#ifndef Py_STATICINIT_H
#define Py_STATICINIT_H

#include "object.h"
#include "import.h"

#define NUITKA_PYTHON_STATIC

#if defined(Py_BUILD_CORE) && !defined(Py_BUILD_CORE_MODULE)
#ifdef __cplusplus
extern "C" {
#endif
"""

    inittab_code = ""

    for module_fullname, filename in foundLibs.items():
        initFunctions = getPythonInitFunctions(compiler, filename)

        if not initFunctions:
            print("Init not found!", module_fullname, filename)
            continue

        module_basename = module_fullname.split(".")[-1]

        module_initfunc_name = ("init" if str is bytes else "PyInit_") + module_basename

        # We might have packages that rename their build functioons.
        if module_initfunc_name not in initFunctions:
            module_initfunc_name = initFunctions[-1]

        staticinitheader += "   extern  PyObject* " + module_initfunc_name + "(void);\n"
        inittab_code += (
                '   PyImport_AppendInittab("'
                + module_fullname
                + '", '
                + module_initfunc_name
                + ");\n"
        )

    staticinitheader += (
            """
    #ifdef __cplusplus
    }
    #endif // __cplusplus

    static inline void Py_InitStaticModules(void) {
    %s
    }

    #endif

    #endif // !Py_STATICINIT_H
    """
            % inittab_code
    )

    with open(
            os.path.join(sysconfig.get_config_var("INCLUDEPY"), "staticinit.h"), "w"
    ) as f:
        f.write(staticinitheader)

    print("Compiling new interpreter...")

    if platform.system() == "Windows":
        interpreter_prefix = sysconfig.get_config_var("srcdir")
    else:
        interpreter_prefix = sysconfig.get_config_var("prefix")

    build_dir = os.path.join(interpreter_prefix, "interpreter_build")

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)

    include_dirs = [sysconfig.get_config_var("INCLUDEPY")]
    macros = [("Py_BUILD_CORE", None)]

    os.chdir(interpreter_prefix)

    if platform.system() == "Windows":
        final_lib_list = []
        for lib in link_libs:
            final_path = lib
            if os.path.isabs(lib):
                final_path = os.path.realpath(lib)
            else:
                for dir in library_dirs:
                    if os.path.isfile(os.path.join(dir, lib)):
                        final_path = os.path.join(dir, lib)
                        break
                    elif os.path.isfile(os.path.join(dir, lib) + ".lib"):
                        final_path = os.path.join(dir, lib) + ".lib"
                        break
            if final_path not in final_lib_list:
                final_lib_list.append(final_path)

        compiler.compile(
            ["python.c"], output_dir=build_dir, include_dirs=include_dirs, macros=macros
        )

        compiler.link_executable(
            [os.path.join(build_dir, "python.obj")],
            "python",
            output_dir=build_dir,
            libraries=final_lib_list,
            library_dirs=library_dirs,
            extra_preargs=["/LTCG", "/USEPROFILE:PGD=python.pgd"],
        )

        # Replace running interpreter by moving current version to a temp file, then marking it for deletion.
        interpreter_path = sys.executable
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        os.unlink(tmp.name)
        os.rename(sys.executable, tmp.name)
        ctypes.windll.kernel32.MoveFileExW(tmp.name, None, MOVEFILE_DELAY_UNTIL_REBOOT)

        os.rename(os.path.join(build_dir, "python.exe"), interpreter_path)
    elif platform.system() == "Linux":
        sysconfig_libs = []
        sysconfig_lib_dirs = []
        for arg in (
                ["-lm", "-pthread", "-lutil", "-ldl"]
                + sysconfig.get_config_var("LDFLAGS").split()
                + sysconfig.get_config_var("CFLAGS").split()
                + sysconfig.get_config_var("MODLIBS").split()
                + sysconfig.get_config_var("LIBS").split()
        ):
            if arg.startswith("-l"):
                if arg[2:] not in sysconfig_libs:
                    sysconfig_libs.append(arg[2:])
            elif arg.startswith("-L"):
                if arg[2:] not in sysconfig_lib_dirs:
                    sysconfig_lib_dirs.append(arg[2:])

        link_libs = sysconfig_libs + link_libs
        libpython_lib = [x for x in link_libs if os.path.basename(x).startswith('libpython') and x.endswith(".a")][0]
        link_libs = [libpython_lib] + [x for x in link_libs if x != libpython_lib]
        library_dirs = sysconfig_lib_dirs + library_dirs

        compiler.compile(
            [os.path.join(sysconfig.get_config_var("prefix"), "python.c")],
            output_dir="/",
            include_dirs=include_dirs,
            macros=macros,
        )

        compiler.link_executable(
            objects=[os.path.join(sysconfig.get_config_var("prefix"), "python.o")],
            output_progname="python",
            output_dir=build_dir,
            libraries=link_libs,
            library_dirs=library_dirs,
            extra_preargs=sysconfig.get_config_var("LDFLAGS").split()
                          + [
                              "-flto",
                              "-fuse-linker-plugin",
                              "-ffat-lto-objects",
                              "-flto-partition=none",
                          ],
        )

        # Replace running interpreter by moving current version to a temp file, then deleting it. This
        # is to avoid Windows locks
        interpreter_path = os.path.realpath(sys.executable)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, dir=os.path.dirname(sys.executable)
        )
        tmp.close()
        os.unlink(tmp.name)
        os.rename(interpreter_path, tmp.name)
        os.unlink(tmp.name)

        os.rename(os.path.join(build_dir, "python"), interpreter_path)

    with open(os.path.join(interpreter_prefix, "link.json"), "w") as f:
        json.dump(
            {
                "include_dirs": include_dirs,
                "macros": macros,
                "libraries": link_libs,
                "library_dirs": library_dirs,
            },
            f,
        )


if __name__ == "__main__":
    run_rebuild()
