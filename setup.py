from distutils.core import setup

from pyjoomatic import __version__


setup(
    name='pyjoomatic',
    version=__version__,
    description='Automating joomla through selenium',
    author='Alex Garel',
    url='https://github.com/alexgarel/pyjoomatic',
    packages=['pyjoomatic'],
    install_requires=[
        'selenium>=3.0.2'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4'])
