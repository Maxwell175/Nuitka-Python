import fnmatch
import json
import os
import sys
import sysconfig
import warnings
import platform

import __np__

# Make the standard pip, the real pip module.
# Need to keep a reference alive, or the module will loose all attributes.
if "pip" in sys.modules:
    _this_module = sys.modules["pip"]
    del sys.modules["pip"]

real_pip_dir = os.path.join(os.path.dirname(__file__), "site-packages")
sys.path.insert(0, real_pip_dir)
import pip as _pip

del sys.path[0]
sys.modules["pip"] = _pip

try:
    import pip._internal.pyproject

    def load_pyproject_toml(use_pep517, pyproject_toml, setup_py, req_name):
        return None

    pip._internal.pyproject.load_pyproject_toml = load_pyproject_toml
except:
    pass

import pip._internal.req.req_install


def urlretrieve(url, output_filename):
    local_filename = __np__.download_file(url, os.path.dirname(output_filename))

    return local_filename


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

    def _importFilePy2(modulename, filename):
        """Import a file for Python version 2."""
        import imp

        result = imp.load_source(modulename, filename)

        # Otherwise there are warnings, when this one imports others.
        result.__file__ = filename
        return result

    def _importFilePy3OldWay(modulename, filename):
        """Import a file for Python versions before 3.5."""
        from importlib.machinery import (  # pylint: disable=I0021,import-error,no-name-in-module
            SourceFileLoader,
        )

        # pylint: disable=I0021,deprecated-method
        return SourceFileLoader(modulename, filename).load_module(modulename)

    def _importFilePy3NewWay(modulename, filename):
        """Import a file for Python versions 3.5+."""
        import importlib.machinery
        import importlib.util  # pylint: disable=I0021,import-error,no-name-in-module

        build_script_spec = importlib.util.spec_from_loader(
            modulename, importlib.machinery.SourceFileLoader(modulename, filename)
        )
        build_script_module = importlib.util.module_from_spec(build_script_spec)
        build_script_spec.loader.exec_module(build_script_module)
        return build_script_module

    if python_version < 0x300:
        return _importFilePy2(modulename, filename)
    elif python_version < 0x350:
        return _importFilePy3OldWay(modulename, filename)
    else:
        return _importFilePy3NewWay(modulename, filename)


PACKAGE_BASE_URL = os.environ.get(
    "NUITKA_PYTHON_PACKAGE_URL",
    "https://raw.githubusercontent.com/Nuitka/Nuitka-Python-packages/master",
)


def getPackageUrl(section, name):
    if platform.system() == "Windows":
        if str is bytes:
            section += "/np27-windows"
        else:
            section += "/np{0}{1}-windows".format(sys.version_info.major, sys.version_info.minor)
    elif platform.system() == "Linux":
        if str is bytes:
            section += "/np27-linux"
        else:
            section += "/np{0}{1}-linux".format(sys.version_info.major, sys.version_info.minor)
    elif platform.system() == "Darwin":
        if str is bytes:
            section += "/np27-macos"
        else:
            section += "/np{0}{1}-macos".format(sys.version_info.major, sys.version_info.minor)

    return "{PACKAGE_BASE_URL}/{section}/{name}".format(
        PACKAGE_BASE_URL=PACKAGE_BASE_URL, section=section, name=name
    )


def getPackageJson(section, name):
    package_dir_url = getPackageUrl(section, name)
    with __np__.TemporaryDirectory() as temp_dir:
        data_filename = urlretrieve(
            "{package_dir_url}/index.json".format(**locals()),
            os.path.join(temp_dir, "index.json"),
        )

        with open(data_filename) as data_file:
            return json.loads(data_file.read())


def getBuildScriptName(dir_name, name):
    return "build_script_" + os.path.basename(dir_name).replace("-", "_") + "_" + name


def install_build_tool(name):
    package_index = getPackageJson("build_tools", name)
    package_dir_url = getPackageUrl("build_tools", name)

    if "build_tools" in package_index:
        for tool in package_index["build_tools"]:
            install_build_tool(tool)

    if os.path.isfile(
        os.path.join(__np__.getToolsInstallDir(), name, "version.txt")
    ):
        with open(
            os.path.join(__np__.getToolsInstallDir(), name, "version.txt"), "r"
        ) as f:
            version = f.read()
            if version == package_index["version"]:
                print("Skipping installed build tool {name}.".format(**locals()))
                return

    print("Setting up build tool {name}...".format(**locals()))

    with __np__.TemporaryDirectory() as temp_dir:
        for file in package_index["files"]:
            urlretrieve(
                "{package_dir_url}/{file}".format(**locals()),
                os.path.join(temp_dir, file),
            )

        build_script_module_name = getBuildScriptName(temp_dir, name)
        initcwd = os.getcwd()
        initenviron = dict(os.environ)

        build_script_module = importFileAsModule(
            build_script_module_name,
            os.path.join(temp_dir, package_index["build_script"]),
        )
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

    with open(
        os.path.join(__np__.getToolsInstallDir(), name, "version.txt"), "w"
    ) as f:
        f.write(package_index["version"])


def install_dependency(name):
    package_index = getPackageJson("dependencies", name)
    package_dir_url = getPackageUrl("dependencies", name)

    if "build_tools" in package_index:
        for tool in package_index["build_tools"]:
            install_build_tool(tool)
    if "dependencies" in package_index:
        for dep in package_index["dependencies"]:
            install_dependency(dep)

    if os.path.isfile(
        os.path.join(__np__.getDependencyInstallDir(), name, "version.txt")
    ):
        with open(
            os.path.join(__np__.getDependencyInstallDir(), name, "version.txt"), "r"
        ) as f:
            version = f.read()
            if version == package_index["version"]:
                print("Skipping installed dependency {name}.".format(**locals()))
                return

    print("Compiling dependency {name}...".format(**locals()))

    with __np__.TemporaryDirectory() as temp_dir:
        for file in package_index["files"]:
            urlretrieve(
                "{package_dir_url}/{file}".format(**locals()),
                os.path.join(temp_dir, file),
            )

        build_script_module_name = getBuildScriptName(temp_dir, name)
        initcwd = os.getcwd()
        initenviron = dict(os.environ)

        build_script_module = importFileAsModule(
            build_script_module_name,
            os.path.join(temp_dir, package_index["build_script"]),
        )
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

    with open(
        os.path.join(__np__.getDependencyInstallDir(), name, "version.txt"), "w"
    ) as f:
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
        pycompile=True,
    ):
        fallback = False

        try:
            package_index = getPackageJson("packages", self.name)
        except __np__.NoSuchURL:
            fallback = True
        except:
            if self.name == "certifi":
                fallback = True
            else:
                throw

        if fallback or not self.source_dir:
            __np__.my_print("FALLBACK to standard install for %s" % self.name)

            return _InstallRequirement.install(
                self,
                install_options,
                global_options,
                root,
                home,
                prefix,
                warn_script_location,
                use_user_site,
                pycompile,
            )

        matched_source = None
        for source in package_index["scripts"]:
            for key, value_glob in source["metadata"].items():
                if not fnmatch.fnmatch(self.metadata[key], value_glob):
                    matched_metadata = False
                    break
            else:
                matched_metadata = True

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
            package_dir_url = getPackageUrl("packages", self.name)
            urlretrieve(
                "{package_dir_url}/{file}".format(**locals()),
                os.path.join(install_temp_dir, file),
            )

        build_script_module_name = getBuildScriptName(install_temp_dir, self.name)

        initcwd = os.getcwd()
        initenviron = dict(os.environ)
        build_script_module = importFileAsModule(
            build_script_module_name,
            os.path.join(install_temp_dir, matched_source["build_script"]),
        )

        static_pattern = matched_source.get("static_pattern")
        if static_pattern is None and os.name == "nt":
            static_pattern = "*"

        # Put to empty, to avoid need to remove it and for easier manual usage.
        os.environ["NUITKA_PYTHON_STATIC_PATTERN"] = static_pattern or ""

        try:
            result = build_script_module.run(install_temp_dir, self.source_dir)
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
            _InstallRequirement.install(
                self,
                install_options,
                global_options,
                root,
                home,
                prefix,
                warn_script_location,
                use_user_site,
                pycompile,
            )

        if not int(os.environ.get("NUITKA_PYTHON_MANUAL_REBUILD", "0")):
            import rebuildpython

            rebuildpython.run_rebuild()


pip._internal.req.req_install.InstallRequirement = InstallRequirement


import pip._internal.index.package_finder
from pip._internal import wheel_builder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link

_PackageFinder = pip._internal.index.package_finder.PackageFinder


def build_stub(
    requirements,  # type: Iterable[InstallRequirement]
    wheel_cache,  # type: WheelCache
    verify,  # type: bool
    build_options,  # type: List[str]
    global_options,  # type: List[str]
):
    for r in requirements:
        r.use_pep517 = False
    return [], requirements


wheel_builder.build = build_stub


class PackageFinder(_PackageFinder):
    def find_all_candidates(self, project_name):
        base_candidates = _PackageFinder.find_all_candidates(self, project_name)

        try:
            package_index = getPackageJson("packages", project_name)
        except __np__.NoSuchURL:
            return base_candidates

        package_sources = []
        if "sources" in package_index:
            for source in package_index["sources"]:
                package_sources.append(
                    InstallationCandidate(
                        project_name, source["version"], Link(source["link"])
                    )
                )

        return package_sources + base_candidates


pip._internal.index.package_finder.PackageFinder = PackageFinder


def main():
    # Work around the error reported in #9540, pending a proper fix.
    # Note: It is essential the warning filter is set *before* importing
    #       pip, as the deprecation happens at import time, not runtime.
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, module=".*packaging\\.version"
    )

    if sysconfig.get_config_var("CC"):
        cc_config_var = sysconfig.get_config_var("CC").split()[0]
        if "CC" in os.environ and os.environ["CC"] != cc_config_var:
            print("Overriding CC variable to Nuitka-Python used '%s' ..." % cc_config_var)
        os.environ["CC"] = cc_config_var

    if sysconfig.get_config_var("CXX"):
        cxx_config_var = sysconfig.get_config_var("CXX").split()[0]
        if "CXX" in os.environ and os.environ["CXX"] != cxx_config_var:
            print("Overriding CXX variable to Nuitka-Python used '%s' ..." % cxx_config_var)
        os.environ["CXX"] = cxx_config_var

    import site

    for path in site.getsitepackages():
        # Note: Some of these do not exist, at least on Linux.
        if os.path.exists(path) and not os.access(path, os.W_OK):
            sys.exit("Error, cannot write to '%s', but that is required." % path)

    from pip._internal.cli.main import main as _main

    sys.exit(_main())


if __name__ == "__main__":
    main()
