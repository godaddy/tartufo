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
    name='tartufo',
    version='0.0.1',
    description='tartufo is a tool for scanning git repositories for secrets/passwords/high-entropy data',
    long_description='Seaches for secrets/high-entropy/passwords in git histories and pre-commit blobs '
                     'with the intent to provide developers a way of preventing accidental leaking of '
                     'privileged data. This project was inspired by Dylan Ayrey\'s project truffleHog '
                     'https://github.com/dxa4481/truffleHog',
    url='https://github.com/godaddy/tartufo',
    download_url='https://pypi.org/project/tartufo/#files',
    author='GoDaddy',
    author_email='oss@godaddy.com',
    license='GNU',
    packages=['tartufo'],
    install_requires=INSTALL_REQUIRES,
    setup_requires='',
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        'console_scripts': ['tartufo = tartufo.tartufo:main'],
    },
)
