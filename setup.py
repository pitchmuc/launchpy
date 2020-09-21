import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="launchpy",  # Replace with your own username
    version="0.2.1",
    author="Julien Piccini",
    author_email="piccini.julien@gmail.com",
    description="Python wrapper around the Adobe Experience Launch API.",
    long_description="Full documentation can be found here : https://github.com/pitchmuc/pylaunch/blob/master/README.md",
    long_description_content_type="text/markdown",
    url="https://github.com/pitchmuc/pylaunch",
    packages=setuptools.find_packages(),
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
