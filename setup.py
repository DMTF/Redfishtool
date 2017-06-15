from setuptools import setup

setup(name='redfishtool',
      version='1.0.1',
      description='Redfishtool package and command-line client',
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
      download_url='https://github.com/DMTF/Redfishtool/archive/1.0.1.tar.gz',
      packages=['redfishtool'],
      scripts=['scripts/redfishtool'],
      install_requires=['requests']
      )
