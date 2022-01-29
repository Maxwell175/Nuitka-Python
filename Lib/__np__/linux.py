from .common import *


def get_compiler_module():
    __import__("distutils.unixccompiler")
    return sys.modules["distutils.unixccompiler"]


def make(*args):
    return run_with_output("make", *args)


def auto_patch_Cython_memcpy(folder):
    # TODO: Have a generic implementation, maybe in nuitka.utils for this
    for dname, dirs, files in os.walk(folder):
        for fname in files:
            fpath = os.path.join(dname, fname)
            if ".git" in fpath or ".svn" in fpath:
                continue

            # TODO: Probably unnecessary
            if fname.endswith(".cc"):
                with open(fpath, "r") as f:
                    s = f.read()
                s2 = s.replace('"-Wl,-wrap,memcpy"', "")

                if s != s2:
                    my_print("Removed Cython config: %s" % fpath, style="blue")
                    with open(fpath, "w") as f:
                        f.write(s2)

            if fname == "setup.py":
                with open(fpath, "r") as f:
                    s = f.read()
                s2 = s.replace("-Wl,-wrap,memcpy", "")

                if s != s2:
                    my_print("Removed memcpy wrapper config: %s" % fpath, style="blue")
                    with open(fpath, "w") as f:
                        f.write(s2)
