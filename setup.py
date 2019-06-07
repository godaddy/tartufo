from setuptools import setup

INSTALL_REQUIRES = [
    'GitPython == 2.1.1',
    'truffleHogRegexes == 0.0.7'
]

DATABASE_REQUIRES = [
]

INTERNAL_REQUIRES = [
                    ] + DATABASE_REQUIRES

EXTRAS_REQUIRE = {
    'database': DATABASE_REQUIRES,
    'internal': INTERNAL_REQUIRES,
    'tests': [
        'coverage',
        'flake8',
        'nose',
        'nose-timer',
        'nose-xunitmp',
        'pylint',
        'pyflakes',
        'test',
        'tox',
        'twine',
        'vulture',
        'wheel',
    ]
}
EXTRAS_REQUIRE['tests'].extend(EXTRAS_REQUIRE['internal'])

setup(
    name='gd-truffleHog',
    version='2.0.99',
    description='Searches through git repositories for high entropy strings, digging deep into commit history.',
    url='https://github.com/godaddy/truffleHog',
    author='Dylan Ayrey',
    author_email='dxa4481@rit.edu',
    maintainer='GoDaddy',
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
