import sys
import os
import importlib
import json
import fnmatch
import tempfile
import __np__

# Portability:
if str is bytes:
    from urllib import (  # pylint: disable=I0021,import-error,no-name-in-module
        urlretrieve,
    )
else:
    from urllib.request import urlretrieve

# For Nuitka utils source compatibility
def _getPythonVersion():
    big, major, minor = sys.version_info[0:3]

    # TODO: Give up on decimal versions already.
    return big * 256 + major * 16 + min(15, minor)

python_version = _getPythonVersion()

# Portability, lending an import code to module function from Nuitka.
def importFileAsModule(modulename, filename):
    """Import Python module given as a file name.

    Notes:
        Provides a Python version independent way to import any script files.

    Args:
        filename: complete path of a Python script

    Returns:
        Imported Python module with code from the filename.
    """
    assert os.path.exists(filename), filename

    def importFilePy2(modulename, filename):
        """Import a file for Python version 2."""
        import imp

        return imp.load_source(modulename, filename)

    def _importFilePy3OldWay(modulename, filename):
        """Import a file for Python versions before 3.5."""
        from importlib.machinery import (  # pylint: disable=I0021,import-error,no-name-in-module
            SourceFileLoader,
        )

        # pylint: disable=I0021,deprecated-method
        return SourceFileLoader(modulename, filename).load_module(modulename)

    def _importFilePy3NewWay(modulename, filename):
        """Import a file for Python versions 3.5+."""
        import importlib.util  # pylint: disable=I0021,import-error,no-name-in-module

        script_spec = importlib.util.spec_from_loader(
            modulename,
            importlib.machinery.SourceFileLoader(modulename, filename)
        )
        script_module = importlib.util.module_from_spec(script_spec)
        return script_module

    if python_version < 0x300:
        return importFilePy2(filename)
    elif python_version < 0x350:
        return _importFilePy3OldWay(filename)
    else:
        return _importFilePy3NewWay(filename)


PACKAGE_BASE_URL = os.environ.get("NUITKA_PYTHON_PACKAGE_URL", "https://raw.githubusercontent.com/Nuitka/Nuitka-Python-packages/master")

def getPackageUrl(section, name):
    if section == "packages":
        if os.name == "nt":
            if str is bytes:
                section = "packages/np27-windows"
            else:
                section = "packages/np3-windows"
        else:
            if str is bytes:
                section = "packages/np27-linux"
            else:
                section = "packages/np3-linux"

    return "{PACKAGE_BASE_URL}/{section}/{name}".format(PACKAGE_BASE_URL=PACKAGE_BASE_URL, section=section, name=name)

real_pip_dir = os.path.join(os.path.dirname(__file__), 'site-packages')
sys.path.insert(0, real_pip_dir)
import pip as _pip
del sys.path[0]

sys.modules['pip'] = _pip

import pip._internal.req.req_install


def install_build_tool(name):
    package_dir_url = "{PACKAGE_BASE_URL}/build_tools/{name}".format(PACKAGE_BASE_URL=PACKAGE_BASE_URL, **locals())
    data = urllib.request.urlopen("{package_dir_url}/index.json".format(**locals())).read()
    package_index = json.loads(data)
    if 'build_tools' in package_index:
        for tool in package_index['build_tools']:
            install_build_tool(tool)

    if os.path.isfile(os.path.join(__np__.BUILD_TOOLS_INSTALL_DIR, name, 'version.txt')):
        with open(os.path.join(__np__.BUILD_TOOLS_INSTALL_DIR, name, 'version.txt'), 'r') as f:
            version = f.read()
            if version == package_index['version']:
                print("Skipping installed build tool {name}.".format(**locals()))
                return

    print("Setting up build tool {name}...".format(**locals()))

    with tempfile.TemporaryDirectory() as temp_dir:
        for file in package_index["files"]:
            urlretrieve("{package_dir_url}/{file}".format(**locals()), os.path.join(temp_dir, file))

        build_script_module_name = "build_script{os.path.basename(temp_dir)}.{name}".format(**locals())
        initcwd = os.getcwd()
        initenviron = dict(os.environ)

        build_script_module = importFileAsModule(os.path.join(temp_dir, package_index["build_script"]))
        try:
            build_script_module.run(temp_dir)
        finally:
            if build_script_module_name in sys.modules:
                del sys.modules[build_script_module_name]
            try:
                del build_script_module
            except NameError:
                pass
            os.chdir(initcwd)
            os.environ.clear()
            os.environ.update(initenviron)

    with open(os.path.join(__np__.BUILD_TOOLS_INSTALL_DIR, name, 'version.txt'), 'w') as f:
        f.write(package_index["version"])


def install_dependency(name):
    package_dir_url = getPackageUrl(section="dependencies", name=name)

    data = urlretrieve("{package_dir_url}/index.json".format(**locals()))
    package_index = json.loads(data)
    if 'build_tools' in package_index:
        for tool in package_index['build_tools']:
            install_build_tool(tool)
    if 'dependencies' in package_index:
        for dep in package_index['dependencies']:
            install_dependency(dep)

    if os.path.isfile(os.path.join(__np__.DEPENDENCY_INSTALL_DIR, name, 'version.txt')):
        with open(os.path.join(__np__.DEPENDENCY_INSTALL_DIR, name, 'version.txt'), 'r') as f:
            version = f.read()
            if version == package_index['version']:
                print("Skipping installed dependency {name}.".format(**locals()))
                return

    print("Compiling dependency {name}...".format(**locals()))

    with tempfile.TemporaryDirectory() as temp_dir:
        for file in package_index["files"]:
            urlretrieve("{package_dir_url}/{file}".format(**locals()), os.path.join(temp_dir, file))

        build_script_module_name = "build_script{os.path.basename(temp_dir)}.{name}".format(**locals())
        initcwd = os.getcwd()
        initenviron = dict(os.environ)

        build_script_module = importFileAsModule(os.path.join(temp_dir, package_index["build_script"]))
        try:
            build_script_module.run(temp_dir)
        finally:
            if build_script_module_name in sys.modules:
                del sys.modules[build_script_module_name]
            try:
                del build_script_module
            except NameError:
                pass
            os.chdir(initcwd)
            os.environ.clear()
            os.environ.update(initenviron)

    with open(os.path.join(__np__.DEPENDENCY_INSTALL_DIR, name, 'version.txt'), 'w') as f:
        f.write(package_index["version"])


_InstallRequirement = pip._internal.req.req_install.InstallRequirement


class InstallRequirement(_InstallRequirement):
    def install(
            self,
            install_options,
            global_options=None,
            root=None,
            home=None,
            prefix=None,
            warn_script_location=True,
            use_user_site=False,
            pycompile=True
    ):
        package_dir_url = getPackageUrl(section="packages", name=self.name)

        try:
            fallback = False
            data_filename, _message = urlretrieve("{package_dir_url}/index.json".format(**locals()))

            with open(data_filename) as data_file:
                line = data_file.readline()

                if line.startswith("404:"):
                    # Fall back to using normal pip install.
                    fallback = True
        except EnvironmentError:
            fallback = True

        if fallback:
            print("FALLBACK for %s" % self.name)

            return _InstallRequirement.install(self, install_options, global_options, root, home, prefix, warn_script_location, use_user_site, pycompile)

        with open(data_filename) as data_file:
            package_index = json.load(data_file)

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
            urlretrieve("{package_dir_url}/{file}".format(**locals()), os.path.join(install_temp_dir, file))

        build_script_module_name = "build_script_{uid}.{name}".format(
            uid = os.path.basename(install_temp_dir),
            name = self.name
        )

        initcwd = os.getcwd()
        initenviron = dict(os.environ)
        build_script_module = importFileAsModule(os.path.join(install_temp_dir, matched_source["build_script"]))

        try:
            result = build_script_module.run(self, install_temp_dir, self.source_dir, install_options, global_options, root, home, prefix, warn_script_location, use_user_site, pycompile)
        finally:
            if build_script_module_name in sys.modules:
                del sys.modules[build_script_module_name]
            try:
                del build_script_module
            except NameError:
                pass
            os.chdir(initcwd)
            os.environ.clear()
            os.environ.update(initenviron)

        if result:
            return _InstallRequirement.install(self, install_options, global_options, root, home, prefix, warn_script_location, use_user_site, pycompile)


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
