from setuptools import setup

setup(name='redfishtool',
      version='1.0.0',
      description='Redfishtool package and command-line client',
      author='DMTF',
      author_email='DMTF@DMTF.com',
      license='BSD 3-clause "New" or "Revised License"',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3.4',
          'Topic :: Communications'
      ],
      keywords='Redfish',
      url='https://github.com/DMTF/Redfishtool',
      packages=['redfishtool'],
      scripts=['redfishtool.py'],
      install_requires=['requests']
      )
