import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='check-puppet-agent',
    version='1.0.0',
    url='https://github.com/wywygmbh/check-puppet-agent',
    license='GPLv2',
    author='Christian Becker',
    author_email='christian.becker@wywy.com',
    description='A check to monitor puppet agent runs',
    long_description=read('README.md'),
    packages=['check_puppet_agent'],
    scripts=['check-puppet-agent'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'argparse',
        'Pyaml',
        'six'
    ],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Systems Administration',
    ]
)