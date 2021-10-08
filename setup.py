#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Define publication options."""

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command  # type: ignore

# Package meta-data.
NAME = "tesla_dashcam"
DESCRIPTION = "Python program to merge video files created by Tesla " "dashcam"
URL = "https://github.com/ehendrix23/tesla_dashcam"
EMAIL = "hendrix_erik@hotmail.com"
AUTHOR = "Erik Hendrix"
REQUIRES_PYTHON = ">=3.8.6"
VERSION = None

# What packages are required for this module to be executed?
REQUIRED = [  # type: ignore
    "tzlocal",
    "requests",
    "psutil",
    "python-dateutil",
    "staticmap",
]

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for
# that!

HERE = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.rst' is present in your MANIFEST.in file!
with io.open(os.path.join(HERE, "README.rst"), encoding="utf-8") as f:
    LONG_DESC = "\n" + f.read()

# Load the package's __version__.py module as a dictionary.
ABOUT = {}  # type: ignore
if not VERSION:
    with open(os.path.join(HERE, NAME, "__version__.py")) as f:
        exec(f.read(), ABOUT)  # pylint: disable=exec-used
else:
    ABOUT["__version__"] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []  # type: ignore

    @staticmethod
    def status(string):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(string))

    def initialize_options(self):
        """Add options for initialization."""
        pass

    def finalize_options(self):
        """Add options for finalization."""
        pass

    def run(self):
        """Run."""
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(HERE, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPi via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(ABOUT["__version__"]))
        os.system("git push --tags")

        sys.exit()


class TestUploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package to TestPyPi."
    user_options = []  # type: ignore

    @staticmethod
    def status(string):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(string))

    def initialize_options(self):
        """Add options for initialization."""
        pass

    def finalize_options(self):
        """Add options for finalization."""
        pass

    def run(self):
        """Run."""
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(HERE, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to TestPyPi via Twine…")
        os.system(
            "twine upload --repository-url " "https://test.pypi.org/legacy/ dist/*"
        )

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(ABOUT["__version__"]))
        os.system("git push --tags")

        sys.exit()


class TestUploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package to TestPyPi."
    user_options = []  # type: ignore

    @staticmethod
    def status(string):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(string))

    def initialize_options(self):
        """Add options for initialization."""
        pass

    def finalize_options(self):
        """Add options for finalization."""
        pass

    def run(self):
        """Run."""
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(HERE, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to TestPyPi via Twine…")
        os.system(
            "twine upload --repository-url " "https://test.pypi.org/legacy/ dist/*"
        )

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(ABOUT["__version__"]))
        os.system("git push --tags")

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=ABOUT["__version__"],
    description=DESCRIPTION,
    long_description=LONG_DESC,
    long_description_content_type="text/x-rst",
    author=AUTHOR,
    # author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=("tests",)),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['tesla_dashcam'],
    entry_points={"console_scripts": ["tesla_dashcam=tesla_dashcam:main"]},
    install_requires=REQUIRED,
    include_package_data=True,
    license="Apache License 2.0",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Multimedia :: Video :: Conversion",
    ],
    # $ setup.py publish support.
    cmdclass={"upload": UploadCommand, "testupload": TestUploadCommand},
)
