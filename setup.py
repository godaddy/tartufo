from setuptools import setup

INSTALL_REQUIRES = [
    'GitPython == 2.1.1',
    'truffleHogRegexes == 0.0.7'
]

EXTRAS_REQUIRE = {
    'tests': [
        'tox',
    ]
}

setup(
    name='truffleHog',
    version='2.0.112',
    description='Searches through git repositories for high entropy strings, digging deep into commit history.',
    long_description='Searches through git repositories for secrets, digging deep into commit history and branches. '
                     'This is effective at finding secrets accidentally committed.',
    url='https://github.com/godaddy/truffleHog',
    download_url='https://pypi.org/project/truffleHog/#files',
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
