from .common import *


def get_compiler_module():
    __import__("distutils._msvccompiler")
    return sys.modules["distutils._msvccompiler"]


def get_vs_version():
    compiler_module = get_compiler_module()
    platform = compiler_module.get_platform()
    vc_env = compiler_module._get_vc_env(compiler_module.PLAT_TO_VCVARS[platform])
    return float(vc_env.get("visualstudioversion"))


def find_compiler_exe(exe):
    compiler_module = get_compiler_module()
    platform = compiler_module.get_platform()
    vc_env = compiler_module._get_vc_env(compiler_module.PLAT_TO_VCVARS[platform])
    paths = vc_env.get("path", "").split(os.pathsep)
    return compiler_module._find_exe(exe, paths)


def setup_compiler_env():
    compiler_module = get_compiler_module()
    platform = compiler_module.get_platform()
    vc_env = compiler_module._get_vc_env(compiler_module.PLAT_TO_VCVARS[platform])
    os.environ.update(vc_env)


def run_compiler_exe(exe, *args):
    return run_with_output(find_compiler_exe(exe), *args)


def msbuild(*args):
    return run_compiler_exe("msbuild.exe", *args)


def nmake(*args):
    return run_compiler_exe("nmake.exe", *args)


def auto_patch_MD_MT_file(fpath):
    try:
        if fpath.endswith("CMakeLists.txt"):
            with open(fpath, "r") as f:
                s = f.read()
            s2 = s.replace("/MD", "/MT")
            s2 = s2.replace("-MD", "-MT")
            s2 = re.sub(
                r"cmake_minimum_required *\( *VERSION [0-9\.]+ *\)",
                """cmake_minimum_required(VERSION 3.15)
            set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)
            foreach(flag_var
                        CMAKE_C_FLAGS CMAKE_C_FLAGS_DEBUG CMAKE_C_FLAGS_RELEASE
                        CMAKE_C_FLAGS_MINSIZEREL CMAKE_C_FLAGS_RELWITHDEBINFO
                        CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_RELEASE
                        CMAKE_CXX_FLAGS_MINSIZEREL CMAKE_CXX_FLAGS_RELWITHDEBINFO)
                    if(${flag_var} MATCHES "/MD")
                        string(REGEX REPLACE "/MD" "/MT" ${flag_var} "${${flag_var}}")
                    endif()
                endforeach(flag_var)

         """,
                s2,
                flags=re.IGNORECASE,
            )
            s2 = re.sub(
                r"cmake_policy\(VERSION [0-9\.]+\)", "", s2, flags=re.IGNORECASE
            )
            if s != s2:
                my_print("Fixed up file: %s" % fpath, style="blue")
                with open(fpath, "w") as f:
                    f.write(s2)
        elif not is_file_binary(fpath):
            with open(fpath, "r") as f:
                s = f.read()
            s2 = s.replace("/MD", "/MT")
            s2 = s2.replace("-MD", "-MT")
            if s != s2:
                my_print("Fixed up file: %s" % fpath, style="blue")
                with open(fpath, "w") as f:
                    f.write(s2)
    except Exception:
        pass


def auto_patch_MD_MT(folder):
    for dname, dirs, files in os.walk(folder):
        for fname in files:
            fpath = os.path.join(dname, fname)
            if ".git" in fpath or ".svn" in fpath:
                continue

            auto_patch_MD_MT_file(fpath)
