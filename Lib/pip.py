import fnmatch
import json
import os
import sys
import sysconfig
import warnings
import platform
import rebuildpython
import re

import __np__
import __np__.packaging

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
sys.path.append(real_pip_dir)


import ensurepip
builtin_packages = ensurepip._get_packages()


import pip._internal.utils.subprocess

call_subprocess_orig = pip._internal.utils.subprocess.call_subprocess

def our_call_subprocess(
    cmd,
    show_stdout = False,
    cwd = None,
    on_returncode = "raise",
    extra_ok_returncodes = None,
    extra_environ = None,
    unset_environ = None,
    spinner = None,
    log_failed_cmd = True,
    stdout_only = False,
    *,
    command_desc: str,
):
    if extra_ok_returncodes is None:
        our_extra_ok_returncodes = []
    else:
        our_extra_ok_returncodes = list(extra_ok_returncodes)

    # Some packages cause this error code to be returned even if all is ok.
    our_extra_ok_returncodes += [3221225477]
    return call_subprocess_orig(cmd, show_stdout, cwd, on_returncode, our_extra_ok_returncodes, extra_environ, unset_environ, spinner, log_failed_cmd, stdout_only, command_desc=command_desc)

pip._internal.utils.subprocess.call_subprocess = our_call_subprocess


import pip._internal.pyproject

load_pyproject_toml_orig = pip._internal.pyproject.load_pyproject_toml
def our_load_pyproject_toml(use_pep517, pyproject_toml, setup_py, req_name):
    has_pyproject = os.path.isfile(pyproject_toml)
    has_setup = os.path.isfile(setup_py)

    # We will be taking over the build process.
    if os.path.isfile(os.path.join(os.path.dirname(os.path.dirname(pyproject_toml)), "script.json")):
        return pip._internal.pyproject.BuildSystemDetails(
            [], "__np__.metabuild:managed_build", [], [os.path.dirname(__file__), real_pip_dir])

    result = load_pyproject_toml_orig(use_pep517, pyproject_toml, setup_py, req_name)
    if result is None:
        return None
    return pip._internal.pyproject.BuildSystemDetails(
        [x for x in result.requires if re.split(r'[><=]', x, 1)[0] not in builtin_packages],
        result.backend, result.check, [os.path.dirname(__file__), real_pip_dir] + result.backend_path)



pip._internal.pyproject.load_pyproject_toml = our_load_pyproject_toml


import pip._vendor.pyproject_hooks._impl

def norm_and_dont_check(source_tree, requested):
    abs_source = os.path.abspath(source_tree)
    abs_requested = os.path.normpath(os.path.join(abs_source, requested))
    return abs_requested

pip._vendor.pyproject_hooks._impl.norm_and_check = norm_and_dont_check

import pip._internal.distributions.sdist

orig_SourceDistribution_get_build_requires_wheel = pip._internal.distributions.sdist.SourceDistribution._get_build_requires_wheel
def SourceDistribution_get_build_requires_wheel(self):
    our_source = __np__.packaging.find_source_by_link(self.req.name,self.req.link.url)

    if our_source is not None and "build_requires" in our_source:
        return our_source["build_requires"]

    return orig_SourceDistribution_get_build_requires_wheel(self)



pip._internal.distributions.sdist.SourceDistribution._get_build_requires_wheel = SourceDistribution_get_build_requires_wheel


import pip._internal.index.package_finder
from pip._internal import wheel_builder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link

_PackageFinder = pip._internal.index.package_finder.PackageFinder


class PackageFinder(_PackageFinder):
    def find_all_candidates(self, project_name):
        if project_name in builtin_packages:
            import pathlib

            pkg_version = [x for x in ensurepip._PROJECTS if x[0] == project_name][0][1]

            our_uri = pathlib.Path(os.path.join(os.path.dirname(ensurepip.__file__), '_bundled',
                                                builtin_packages[project_name].wheel_name)).as_uri()
            return [InstallationCandidate(
                project_name, pkg_version, Link(our_uri)
            )]

        base_candidates = _PackageFinder.find_all_candidates(self, project_name)

        return __np__.packaging.get_extra_sources_for_package(project_name) + base_candidates


pip._internal.index.package_finder.PackageFinder = PackageFinder

my_path = os.path.abspath(__file__)

def get_runnable_pip() -> str:
    return my_path


import pip._internal.build_env

pip._internal.build_env.get_runnable_pip = get_runnable_pip

import pip._internal.cli.req_command

orig_get_requirements = pip._internal.cli.req_command.RequirementCommand.get_requirements

def our_get_requirements(self, args, options, finder, session):
    reqs = orig_get_requirements(self, args, options, finder, session)
    # This should prevent accidentally updating the pinned bundled packages.
    return [x for x in reqs if x.req.name not in builtin_packages]

pip._internal.cli.req_command.RequirementCommand.get_requirements = our_get_requirements

import pip._internal.req.req_install

orig_install = pip._internal.req.req_install.InstallRequirement.install


def install(
    self,
    global_options=None,
    root=None,
    home=None,
    prefix=None,
    warn_script_location=True,
    use_user_site=False,
    pycompile=True,
):
    orig_install(self, global_options, root, home, prefix, warn_script_location, use_user_site, pycompile)

    rebuildpython.run_rebuild()


pip._internal.req.req_install.InstallRequirement.install = install


import pip._internal.resolution.resolvelib.candidates
import pip._vendor.pkg_resources

orig_prepare_distribution = pip._internal.resolution.resolvelib.candidates.LinkCandidate._prepare_distribution

def _prepare_distribution(self):
    build_script = __np__.packaging.find_build_script_for_package(self.name, self.version.public)

    if build_script is not None:
        with open(os.path.join(self._factory.preparer.build_dir, 'script.json'), 'w') as f:
            json.dump({
                "name": self.name,
                "version": self.version.public,
                "script_metadata": build_script
            }, f)

    return orig_prepare_distribution(self)

pip._internal.resolution.resolvelib.candidates.LinkCandidate._prepare_distribution = _prepare_distribution


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
