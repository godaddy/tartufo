import codecs
from setuptools import setup

INSTALL_REQUIRES = [
    "click >= 7.0.0, < 8.0.0",
    "GitPython >= 2.1.1, < 4.0.0",
    "pathlib2; python_version < '3.4'",
    "toml >= 0.10.0, < 1.0.0",
    "truffleHogRegexes >= 0.0.7, < 1.0.0",
    "typing; python_version < '3.5'",
]

EXTRAS_REQUIRE = {
    "tests": [
        "black==19.10b0; python_version >= '3.6' and platform_python_implementation == 'CPython'",
        "coverage",
        "mock; python_version == '2.7'",
        "pre-commit",
        "pytest",
        "pytest-cov",
        "pytest-sugar",
        "tox",
        "vulture",
    ]
}


def read(filename):
    with codecs.open(filename, "r", "utf-8") as file_handle:
        return file_handle.read().strip()


setup(
    name="tartufo",
    version=read("VERSION"),
    description="tartufo is a tool for scanning git repositories for secrets/passwords/high-entropy data",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/godaddy/tartufo",
    download_url="https://pypi.org/project/tartufo/#files",
    author="GoDaddy",
    author_email="oss@godaddy.com",
    license="GNU",
    packages=["tartufo"],
    install_requires=INSTALL_REQUIRES,
    setup_requires="",
    extras_require=EXTRAS_REQUIRE,
    entry_points={"console_scripts": ["tartufo = tartufo.cli:main"],},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Security",
        "Topic :: Software Development :: Version Control :: Git",
    ],
)
