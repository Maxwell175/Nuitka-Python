import io
import sys
import os
import glob
import pkgutil
import shutil
import subprocess
import distutils
import distutils.ccompiler
from distutils.sysconfig import get_config_var
import sysconfig
import json
import tempfile
import ctypes
import copy
MOVEFILE_DELAY_UNTIL_REBOOT = 4

def run_rebuild():
    initial_sys_path = copy.deepcopy(sys.path)

    installDir = os.path.dirname(sys.executable)

    for i, path in reversed(list(enumerate(initial_sys_path))):
        if installDir not in path:
            del sys.path[i]

    foundLibs = {}

    compiler = distutils.ccompiler.new_compiler(verbose=5)
    compiler.initialize()

    checkedLibs = set()

    # Scan sys.path for any more lingering static libs.
    for path in sys.path + [os.path.join(sysconfig.get_config_var('srcdir'), 'libs')]:
        if path == installDir:
            continue
        for file in glob.glob(os.path.join(path, '**', '*.lib'), recursive=True):
            if file in checkedLibs:
                continue
            initFunctions = [x.decode('ascii') for x in
                             subprocess.check_output([compiler.dumpbin, '/linkermember', file]).split(b"\r\n") if
                             b'PyInit' in x]
            # If this lib has a PyInit function, we should link it in.
            if initFunctions:
                relativePath = os.path.relpath(file, path)
                if 'site-packages' in relativePath:
                    continue
                relativePath = relativePath.replace(get_config_var('EXT_SUFFIX'), '').replace('.lib', '')
                relativePath = relativePath.replace('\\', '.').replace('/', '.')
                print(relativePath, file)
                foundLibs[relativePath] = file

    print('Scanning for any additional libs to link...')

    # Start with the libs needed for a base interpreter.
    linkLibs = ['advapi32', 'shell32', 'ole32', 'oleaut32', 'kernel32', 'user32', 'gdi32', 'winspool', 'comdlg32', 'uuid', 'odbc32', 'odbccp32', 'shlwapi', 'ws2_32', 'version', 'libssl', 'libcrypto', 'tcl86t', 'tk86t', 'Crypt32', 'Iphlpapi', 'msi', 'Rpcrt4', 'Cabinet', 'winmm']

    library_dirs = [sysconfig.get_config_var('srcdir'), os.path.join(sysconfig.get_config_var('srcdir'), 'libs'), os.path.join(sysconfig.get_config_var('srcdir'), 'tcl')]

    # Scrape all available libs from the libs directory. We will let the linker worry about filtering out extra symbols.
    for file in glob.glob(os.path.join(sysconfig.get_config_var('srcdir'), 'libs', '*.lib')):
        linkLibs.append(file)

    for name, path in foundLibs.items():
        linkLibs += [path]

        if os.path.isfile(path + '.link.json'):
            with open(path + '.link.json', 'r') as f:
                linkData = json.load(f)
                print(linkData)
                linkLibs += linkData['libraries']
                library_dirs += [os.path.join(os.path.dirname(path), x) for x in linkData['library_dirs']]

    linkLibs = list(set(linkLibs))
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

    for key, value in foundLibs.items():
        initFunctions = [x.decode('ascii') for x in subprocess.check_output([compiler.dumpbin, '/linkermember', value]).split(b"\r\n") if b'PyInit' in x]
        if not initFunctions:
            print("Init not found!", key, value)
            continue
        initFunction = [x for x in [y for y in initFunctions if '$' not in y and '@' not in y and '?' not in y][-1].split(' ') if len(x) > 6][-1]
        staticinitheader += "	extern  PyObject* " + initFunction + "(void);\n"


    staticinitheader += """
#ifdef __cplusplus
}
#endif // __cplusplus

inline void Py_InitStaticModules() {
"""

    for key, value in foundLibs.items():
        initFunctions = [x.decode('ascii') for x in subprocess.check_output([compiler.dumpbin, '/linkermember', value]).split(b"\r\n") if b'PyInit' in x]
        if not initFunctions:
            continue
        initFunction = [x for x in [y for y in initFunctions if '$' not in y and '@' not in y and '?' not in y][-1].split(' ') if len(x) > 6][-1]
        staticinitheader += "	PyImport_AppendInittab(\"" + key + "\", " + initFunction + ");\n"

    staticinitheader += """
}

#endif

#endif // !Py_STATICINIT_H
"""

    with open(os.path.join(sysconfig.get_config_var('INCLUDEPY'), 'staticinit.h'), 'w') as f:
        f.write(staticinitheader)

    print('Compiling new interpreter...')

    build_dir = os.path.join(sysconfig.get_config_var('srcdir'), 'interpreter_build')

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)

    include_dirs = [sysconfig.get_config_var('INCLUDEPY')]
    macros = [('Py_BUILD_CORE', None)]

    os.chdir(sysconfig.get_config_var('srcdir'))

    compiler.compile(['python.c'], output_dir=build_dir, include_dirs=include_dirs, macros=macros)

    compiler.link_executable([os.path.join(build_dir, 'python.obj')], 'python', output_dir=build_dir, libraries=linkLibs, library_dirs=library_dirs, extra_preargs=["/LTCG", "/USEPROFILE:PGD=python.pgd"])

    # Replace running interpreter by moving current version to a temp file, then marking it for deletion.
    interpreter_path = sys.executable
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    os.unlink(tmp.name)
    os.rename(sys.executable, tmp.name)
    ctypes.windll.kernel32.MoveFileExW(tmp.name, None, MOVEFILE_DELAY_UNTIL_REBOOT)

    os.rename(os.path.join(build_dir, 'python.exe'), interpreter_path)

    with open(os.path.join(sysconfig.get_config_var('srcdir'), 'link.json'), 'w') as f:
        json.dump({
            'include_dirs': include_dirs,
            'macros': macros,
            'libraries': linkLibs,
            'library_dirs': library_dirs
        }, f)

    sys.path = initial_sys_path


if __name__ == '__main__':
    run_rebuild()
