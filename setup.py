# -*- coding: utf-8 -*-

from distutils.core import setup
import os

from setuptools import find_packages


shared_files = []
package_data = {
    'account': [],
    'sokoban': [],
}


def add_directory_to_array(directory, arr):
    for cur, _, files in os.walk(directory):
        arr.extend(os.path.join(cur, f) for f in files)


def copy_directory_to(directory, prefix, pool):
    for cur, _, files in os.walk(directory):
        cur_path = os.path.join(prefix, os.path.relpath(cur, directory))
        pool.append((cur_path, [os.path.join(cur, f) for f in files]))

copy_directory_to('docker/sokoban', '/usr/share/sokoban/docker', shared_files)
copy_directory_to('config', '/etc/sokoban', shared_files)

add_directory_to_array('src/account/templates', package_data['account'])
add_directory_to_array('src/sokoban/templates', package_data['sokoban'])
add_directory_to_array('src/sokoban/static', package_data['sokoban'])


setup(
    name='sokoban',
    version='0.0.1a1',
    author='Jay Lee',
    author_email='busyjaylee@gmail.com',
    description='A project aims to ease the pain of developer synchronizing docs',
    license='MIT',
    keywords='documentation',
    url='https://code.engineering.redhat.com/gerrit/gitweb?p=sokoban.git;a=summary',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Topic :: Documentation',
        'Topic :: Software Development :: Documentation',
    ],
    scripts=['bin/sokoban_manage.py', "bin/sokoban_postinstall.sh", "bin/sokoban_preuninstall.sh"],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        'account': package_data['account'],
        'sokoban': package_data['sokoban'],
    },
    include_package_data=True,
    install_requires=['django>=1.5, <1.6', 'MySQL-python', 'sh', 'sphinx', 'BeautifulSoup4', 'html5lib', 'requests', 'django-suit', 'apscheduler', 'pytz', 'oauth2'],
    data_files=shared_files,
)
