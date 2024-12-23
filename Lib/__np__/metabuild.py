import os
import json
import setuptools.build_meta
import pip._vendor.pkg_resources as pkg_resources

import __np__.packaging

class ManagedBackend():
    def prepare_metadata_for_build_wheel(
        self, metadata_directory, config_settings=None
    ):
        with open(os.path.join("..", "script.json")) as f:
            metadata = json.load(f)
        with open(os.path.join(metadata_directory, "METADATA"), 'w') as f:
            f.write("Metadata-Version: 2.1\n")
            f.write(f"Name: {metadata['name']}\n")
            f.write(f"Version: {metadata['version']}\n")

        return "."

    def build_wheel(
        self,
        wheel_directory,
        config_settings = None,
        metadata_directory = None,
    ):
        with open(os.path.join("..", "script.json")) as f:
            metadata = json.load(f)

        return __np__.packaging.build_package(metadata['name'], metadata['version'], metadata['script_metadata'], wheel_directory)


managed_build = ManagedBackend()
