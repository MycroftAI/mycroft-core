import os
import subprocess
from setuptools import find_packages
import shutil


__author__ = 'seanfitz'

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def place_manifest(manifest_file):
    shutil.copy(manifest_file, "MANIFEST.in")

def get_version():
    version = None
    try:
        import mycroft.__version__
        version = mycroft.__version__.version
    except Exception, e:
        try:
            version = "dev-" + subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip()
        except subprocess.CalledProcessError, e2:
            version = "development"

    return version


def required(requirements_file):
    with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
        requirements = f.read().splitlines()
        return [pkg for pkg in requirements if not pkg.startswith("--")]


def find_all_packages(where):
    packages = find_packages(where=where, exclude=["*test*"])
    return [os.path.join(where, pkg.replace(".", os.sep)) for pkg in packages] + [where]