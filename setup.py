import codecs
import os
from setuptools import setup, find_packages


def read(rel_path: str):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path: str):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="launchpy",  # Replace with your own username
    version=get_version("launchpy/__version__.py"),
    author="Julien Piccini",
    author_email="piccini.julien@gmail.com",
    description="Python wrapper around the Adobe Experience Launch API.",
    long_description="Full documentation can be found here : https://github.com/pitchmuc/launchpy/blob/master/README.md",
    long_description_content_type="text/markdown",
    url="https://github.com/pitchmuc/launchpy",
    packages=find_packages(),
    keywords=['adobe', 'Launch', 'API', 'python', 'Tag Manager'],
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Utilities",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Development Status :: 4 - Beta"
    ],
    python_requires='>=3.7',
    install_requires=['pandas', "requests",
                      "PyJWT", "pathlib2", "pathlib", "PyJWT[crypto]"],
)
