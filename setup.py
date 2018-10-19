from setuptools import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='redfishtool',
      version='1.0.7',
      description='Redfishtool package and command-line client',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='DMTF, https://www.dmtf.org/standards/feedback',
      license='BSD 3-clause "New" or "Revised License"',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3.4',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Communications'
      ],
      keywords='Redfish',
      url='https://github.com/DMTF/Redfishtool',
      download_url='https://github.com/DMTF/Redfishtool/archive/1.0.5.tar.gz',
      packages=['redfishtool'],
      scripts=['scripts/redfishtool'],
      install_requires=['requests']
      )
