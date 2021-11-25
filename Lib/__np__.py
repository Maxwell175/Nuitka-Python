import glob
import os
import sys
import re
import subprocess
import tempfile
import urllib.request
import sysconfig
import shutil
import pathlib
import contextlib

if str is not bytes:
    from typing import *
    from types import ModuleType

DEPENDENCY_INSTALL_DIR = os.path.join(sysconfig.get_config_var('prefix'), 'dependency_libs')
BUILD_TOOLS_INSTALL_DIR = os.path.join(sysconfig.get_config_var('prefix'), 'build_tools')


def download_file(url, destination) -> str:
    with contextlib.closing(urllib.request.urlopen(url)) as fp:
        if 'content-disposition' in fp.headers and 'filename=' in fp.headers['content-disposition']:
            destination_file = os.path.join(destination, fp.headers['content-disposition'].split('filename=')[-1])
        else:
            destination_file = os.path.join(destination, pathlib.Path(fp.url).name)
        with open(destination_file, 'wb') as out_file:
            bs = 1024*8
            while True:
                block = fp.read(bs)
                if not block:
                    break
                out_file.write(block)
    return destination_file


def extract_archive(archive_file: str, destination=None) -> str:
    if destination is None:
        destination = os.path.splitext(archive_file)[0]
        if destination.endswith('.tar'):
            destination = destination[:-4]
    shutil.unpack_archive(archive_file, destination)
    return destination


def download_extract(url: str, destination: str):
    with tempfile.TemporaryDirectory() as dir:
        downloaded_file = download_file(url, dir)
        extract_archive(downloaded_file, destination)


def get_compiler_module() -> ModuleType:
    __import__("distutils._msvccompiler")
    return sys.modules["distutils._msvccompiler"]


def get_vs_version() -> float:
    compiler_module = get_compiler_module()
    platform = compiler_module.get_platform()
    vc_env = compiler_module._get_vc_env(compiler_module.PLAT_TO_VCVARS[platform])
    return float(vc_env.get('visualstudioversion'))


def get_platform() -> str:
    compiler_module = get_compiler_module()
    return compiler_module.get_platform()


def find_compiler_exe(exe: str) -> Type:
    compiler_module = get_compiler_module()
    platform = compiler_module.get_platform()
    vc_env = compiler_module._get_vc_env(compiler_module.PLAT_TO_VCVARS[platform])
    paths = vc_env.get('path', '').split(os.pathsep)
    return compiler_module._find_exe(exe, paths)


def setup_compiler_env():
    compiler_module = get_compiler_module()
    platform = compiler_module.get_platform()
    vc_env = compiler_module._get_vc_env(compiler_module.PLAT_TO_VCVARS[platform])
    os.environ.update(vc_env)


def run_with_output(*args: str) -> str:
    p = subprocess.Popen(args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ""
    for line in p.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        output += line
    p.wait()
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, args, output)
    return output


def run_compiler_exe(exe: str, *args: str):
    return run_with_output(find_compiler_exe(exe), *args)


def msbuild(*args: str) -> str:
    return run_compiler_exe("msbuild.exe", *args)


def nmake(*args: str) -> str:
    return run_compiler_exe("nmake.exe", *args)


def install_files(dst: str, *files: str):
    if not os.path.isdir(dst):
        os.makedirs(dst, exist_ok=True)
    for file_glob in files:
        for file in glob.glob(file_glob):
            if os.path.isdir(file):
                shutil.copytree(file, os.path.join(dst, os.path.basename(file)))
            else:
                shutil.copy(file, os.path.join(dst, os.path.basename(file)))


def install_dep_include(dependency_name: str, *files: str):
    dependency_location = os.path.join(DEPENDENCY_INSTALL_DIR, dependency_name, 'include')
    install_files(dependency_location, *files)


def install_dep_libs(dependency_name: str, *files: str):
    dependency_location = os.path.join(DEPENDENCY_INSTALL_DIR, dependency_name, 'libs')
    install_files(dependency_location, *files)


def install_build_tool(tool_name: str, *files: str):
    dependency_location = os.path.join(BUILD_TOOLS_INSTALL_DIR, tool_name)
    install_files(dependency_location, *files)


def find_build_tool_exe(tool_name: str, exe: str) -> str:
    return glob.glob(os.path.join(BUILD_TOOLS_INSTALL_DIR, tool_name, exe))[0]


def run_build_tool_exe(tool_name: str, exe: str, *args: str) -> str:
    return run_with_output(find_build_tool_exe(tool_name, exe), *args)


def find_dep_include(dep_name: str) -> str:
    return os.path.join(DEPENDENCY_INSTALL_DIR, dep_name, 'include')


def find_dep_libs(dep_name: str) -> str:
    return os.path.join(DEPENDENCY_INSTALL_DIR, dep_name, 'libs')


def prepend_to_file(file: str, prepend_str: str):
    output = prepend_str
    with open(file, 'r') as f:
        output += f.read()
    with open(file, 'w') as f:
        f.write(output)


def is_file_binary(file_path: str) -> bool:
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    with open(file_path, 'rb') as f:
        return bool(f.read(1024).translate(None, textchars))


def auto_patch_MD_MT(folder):
    for dname, dirs, files in os.walk(folder):
        for fname in files:
            fpath = os.path.join(dname, fname)
            if '.git' in fpath or '.svn' in fpath:
                continue

            if fname.endswith('CMakeLists.txt'):
                with open(fpath, 'r') as f:
                    s = f.read()
                s2 = s.replace("/MD", "/MT")
                s2 = s2.replace("-MD", "-MT")
                s2 = re.sub(r"cmake_minimum_required *\( *VERSION [0-9\.]+ *\)", "cmake_minimum_required(VERSION 3.15)", s2, flags=re.IGNORECASE)
                s2 = re.sub(r"cmake_policy\(VERSION [0-9\.]+\)", "", s2, flags=re.IGNORECASE)
                if s != s2:
                    print("Fixed up file:", fpath)
                    with open(fpath, "w") as f:
                        f.write(s2)
            elif not is_file_binary(fpath):
                with open(fpath, 'r') as f:
                    s = f.read()
                s2 = s.replace("/MD", "/MT")
                s2 = s2.replace("-MD", "-MT")
                if s != s2:
                    print("Fixed up file:", fpath)
                    with open(fpath, "w") as f:
                        f.write(s2)


def auto_patch_Cython_memcpy(folder):
    # TODO: Have a generic implementation, maybe in nuitka.utils for this
    for dname, dirs, files in os.walk(folder):
        for fname in files:
            fpath = os.path.join(dname, fname)
            if '.git' in fpath or '.svn' in fpath:
                continue

            # TODO: Probably unnecessary
            if fname.endswith('.cc'):
                with open(fpath, 'r') as f:
                    s = f.read()
                s2 = s.replace('"-Wl,-wrap,memcpy"',"")

                if s != s2:
                    print("Removed Cython config:", fpath)
                    with open(fpath, "w") as f:
                        f.write(s2)


            if fname == "setup.py":
                with open(fpath, 'r') as f:
                    s = f.read()
                s2 = s.replace("-Wl,-wrap,memcpy", "")

                if s != s2:
                    print("Removed memcpy wrapper config:", fpath)
                    with open(fpath, "w") as f:
                        f.write(s2)

