import glob
import sys
import os
import importlib
import json
import urllib.request
import fnmatch
import importlib.util
import tempfile
import nputils
from importlib.machinery import SourceFileLoader

PACKAGE_BASE_URL = "https://raw.githubusercontent.com/Nuitka/Nuitka-Python-packages/master"
#PACKAGE_BASE_URL = "file:///C:/src/Nuitka-Python-packages"

_pip = importlib.import_module('site-packages.pip')

_pip.__name__ = 'pip'

sys.modules['pip'] = _pip

import pip._internal.req.req_install
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.utils.temp_dir import TempDirectory


def install_build_tool(name: str):
    package_dir_url = f"{PACKAGE_BASE_URL}/build_tools/{name}"
    data = urllib.request.urlopen(f"{package_dir_url}/index.json").read()
    package_index = json.loads(data)
    if 'build_tools' in package_index:
        for tool in package_index['build_tools']:
            install_build_tool(tool)

    if os.path.isfile(os.path.join(nputils.BUILD_TOOLS_INSTALL_DIR, name, 'version.txt')):
        with open(os.path.join(nputils.BUILD_TOOLS_INSTALL_DIR, name, 'version.txt'), 'r') as f:
            version = f.read()
            if version == package_index['version']:
                print(f"Skipping installed build tool {name}.")
                return

    print(f"Setting up build tool {name}...")

    with tempfile.TemporaryDirectory() as temp_dir:
        for file in package_index["files"]:
            urllib.request.urlretrieve(f"{package_dir_url}/{file}", os.path.join(temp_dir, file))

        build_script_module_name = f"build_script{os.path.basename(temp_dir)}.{name}"
        initcwd = os.getcwd()
        initenviron = dict(os.environ)
        try:
            build_script_spec = importlib.util.spec_from_loader(
                build_script_module_name,
                importlib.machinery.SourceFileLoader(build_script_module_name, os.path.join(temp_dir, package_index["build_script"]))
            )
            build_script_module = importlib.util.module_from_spec(build_script_spec)
            build_script_spec.loader.exec_module(build_script_module)
            build_script_module.run(temp_dir)
        finally:
            if build_script_module_name in sys.modules:
                del sys.modules[build_script_module_name]
            try:
                del build_script_module
            except NameError:
                pass
            try:
                del build_script_spec
            except NameError:
                pass
            os.chdir(initcwd)
            os.environ.clear()
            os.environ.update(initenviron)

    with open(os.path.join(nputils.BUILD_TOOLS_INSTALL_DIR, name, 'version.txt'), 'w') as f:
        f.write(package_index["version"])


def install_dependency(name: str):
    package_dir_url = f"{PACKAGE_BASE_URL}/dependencies/{name}"
    data = urllib.request.urlopen(f"{package_dir_url}/index.json").read()
    package_index = json.loads(data)
    if 'build_tools' in package_index:
        for tool in package_index['build_tools']:
            install_build_tool(tool)
    if 'dependencies' in package_index:
        for dep in package_index['dependencies']:
            install_dependency(dep)

    if os.path.isfile(os.path.join(nputils.DEPENDENCY_INSTALL_DIR, name, 'version.txt')):
        with open(os.path.join(nputils.DEPENDENCY_INSTALL_DIR, name, 'version.txt'), 'r') as f:
            version = f.read()
            if version == package_index['version']:
                print(f"Skipping installed dependency {name}.")
                return

    print(f"Compiling dependency {name}...")

    with tempfile.TemporaryDirectory() as temp_dir:
        for file in package_index["files"]:
            urllib.request.urlretrieve(f"{package_dir_url}/{file}", os.path.join(temp_dir, file))

        build_script_module_name = f"build_script{os.path.basename(temp_dir)}.{name}"
        initcwd = os.getcwd()
        initenviron = dict(os.environ)
        try:
            build_script_spec = importlib.util.spec_from_loader(
                build_script_module_name,
                importlib.machinery.SourceFileLoader(build_script_module_name, os.path.join(temp_dir, package_index["build_script"]))
            )
            build_script_module = importlib.util.module_from_spec(build_script_spec)
            build_script_spec.loader.exec_module(build_script_module)
            build_script_module.run(temp_dir)
        finally:
            if build_script_module_name in sys.modules:
                del sys.modules[build_script_module_name]
            try:
                del build_script_module
            except NameError:
                pass
            try:
                del build_script_spec
            except NameError:
                pass
            os.chdir(initcwd)
            os.environ.clear()
            os.environ.update(initenviron)

    with open(os.path.join(nputils.DEPENDENCY_INSTALL_DIR, name, 'version.txt'), 'w') as f:
        f.write(package_index["version"])


_InstallRequirement = pip._internal.req.req_install.InstallRequirement


class InstallRequirement(_InstallRequirement):
    def install(
            self,
            install_options,  # type: List[str]
            global_options=None,  # type: Optional[Sequence[str]]
            root=None,  # type: Optional[str]
            home=None,  # type: Optional[str]
            prefix=None,  # type: Optional[str]
            warn_script_location=True,  # type: bool
            use_user_site=False,  # type: bool
            pycompile=True  # type: bool
    ):
        try:
            package_dir_url = f"{PACKAGE_BASE_URL}/packages/{self.name}"
            data = urllib.request.urlopen(f"{package_dir_url}/index.json").read()
            package_index = json.loads(data)
            matched_source = None
            for source in package_index["scripts"]:
                matched_metadata = True
                for key, value_glob in source["metadata"].items():
                    if not fnmatch.fnmatch(self.metadata[key], value_glob):
                        matched_metadata = False
                if matched_metadata:
                    matched_source = source
                    break

            install_temp_dir = os.path.dirname(self.source_dir)

            if "build_tools" in matched_source:
                for dep in matched_source["build_tools"]:
                    install_build_tool(dep)

            if "dependencies" in matched_source:
                for dep in matched_source["dependencies"]:
                    install_dependency(dep)

            for file in matched_source["files"]:
                urllib.request.urlretrieve(f"{package_dir_url}/{file}", os.path.join(install_temp_dir, file))


            build_script_module_name = f"build_script{os.path.basename(install_temp_dir)}.{self.name}"
            initcwd = os.getcwd()
            initenviron = dict(os.environ)
            try:
                build_script_spec = importlib.util.spec_from_loader(
                    build_script_module_name,
                    importlib.machinery.SourceFileLoader(build_script_module_name, os.path.join(install_temp_dir, matched_source["build_script"]))
                )
                build_script_module = importlib.util.module_from_spec(build_script_spec)
                build_script_spec.loader.exec_module(build_script_module)
                build_script_module.run(self, install_temp_dir, self.source_dir, install_options, global_options, root, home, prefix, warn_script_location, use_user_site, pycompile)
            finally:
                if build_script_module_name in sys.modules:
                    del sys.modules[build_script_module_name]
                try:
                    del build_script_module
                except NameError:
                    pass
                try:
                    del build_script_spec
                except NameError:
                    pass
                os.chdir(initcwd)
                os.environ.clear()
                os.environ.update(initenviron)
        except urllib.request.HTTPError:
            # Fall back to using normal pip install.
            _InstallRequirement.install(self, install_options, global_options, root, home, prefix, warn_script_location, use_user_site, pycompile)


pip._internal.req.req_install.InstallRequirement = InstallRequirement

if __name__ == "__main__":
    import warnings
    # Work around the error reported in #9540, pending a proper fix.
    # Note: It is essential the warning filter is set *before* importing
    #       pip, as the deprecation happens at import time, not runtime.
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, module=".*packaging\\.version"
    )
    from pip._internal.cli.main import main as _main

    sys.exit(_main())
