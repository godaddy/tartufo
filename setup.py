from setuptools import setup

INSTALL_REQUIRES = [
    'GitPython == 2.1.1',
    'truffleHogRegexes == 0.0.7'
]

EXTRAS_REQUIRE = {
    'tests': [
        'unittest2 == 1.1.0',
        'pytest-cov == 2.5.1',
        'codecov == 2.0.15',
        'pylint',
        'mock'
    ]
}

setup(
    name='truffleHog',
    version='2.0.98',
    description='Searches through git repositories for high entropy strings, digging deep into commit history.',
    url='https://github.com/dxa4481/truffleHog',
    author='Dylan Ayrey',
    author_email='dxa4481@rit.edu',
    license='GNU',
    packages=['truffleHog'],
    install_requires=INSTALL_REQUIRES,
    setup_requires='',
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        'console_scripts': ['trufflehog = truffleHog.truffleHog:main'],
    },
)
