#!/usr/bin/env python

from distutils.core import setup, Command
from distutils.spawn import find_executable
import os

protoc = find_executable("protoc")


class BuildPbfCommand(Command):
    description = "build protocol buffer files"
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('{protoc} -Ichaos-proto --python_out=kirin chaos-proto/*.proto'.format(protoc=protoc))


setup(
    name='kirin',
    cmdclass={'build_pbf': BuildPbfCommand}
)

