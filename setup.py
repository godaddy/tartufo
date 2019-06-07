from setuptools import setup, find_packages

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
    packages = ['truffleHog'],
    install_requires=[
        'GitPython == 2.1.1',
        'truffleHogRegexes == 0.0.7'
    ],
    entry_points = {
      'console_scripts': ['trufflehog = truffleHog.truffleHog:main'],
    },
)
