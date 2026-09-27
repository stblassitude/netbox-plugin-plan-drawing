"""
Package metadata lives in pyproject.toml. This file only hooks the draw.io download into the
build, so that every wheel ships with the bundled draw.io web application.
"""
import importlib.util
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


def load_fetch_drawio():
    path = Path(__file__).resolve().parent / 'scripts' / 'fetch_drawio.py'
    spec = importlib.util.spec_from_file_location('fetch_drawio', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildPyWithDrawio(build_py):
    def run(self):
        load_fetch_drawio().install()
        # The list of package data files is computed lazily; make sure it is computed
        # after draw.io has been unpacked.
        self.__dict__.pop('data_files', None)
        super().run()


setup(cmdclass={'build_py': BuildPyWithDrawio})
