from setuptools import setup

INSTALL_REQUIRES = [
    'GitPython == 2.1.1',
    'truffleHogRegexes == 0.0.7'
]

EXTRAS_REQUIRE = {
    'tests': [
        'codecov',
        'coverage',
        'flake8',
        'mock',
        'mypy>=0.670,<1; platform_python_implementation == "CPython"',
        'nose',
        'nose-timer',
        'nose-xunitmp',
        'pylint',
        'pyflakes',
        'pytest-cov',
        'test',
        'tox',
        'twine',
        'unittest2',
        'wheel',
    ]
}

setup(
    name='gd-truffleHog',
    version='2.0.100',
    description='Searches through git repositories for high entropy strings, digging deep into commit history.',
    url='https://github.com/godaddy/truffleHog',
    author='Dylan Ayrey',
    author_email='dxa4481@rit.edu',
    maintainer='GoDadddy',
    maintainer_email='dev_common_services@godaddy.com',
    license='GNU',
    packages=['truffleHog'],
    install_requires=INSTALL_REQUIRES,
    setup_requires='',
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        'console_scripts': ['trufflehog = truffleHog.truffleHog:main'],
    },
)
