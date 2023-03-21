from setuptools import setup

setup(name='pyawshelpers',
      version='0.1',
      description='Python helper classes and functions for AWS API',
      url='http://github.com/gmarchand/pyawshelpers',
      author='Guillaume Marchand',
      author_email='gmarchan@amazon.com',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.9'
      ],
      packages=['pyawshelpers'],
      zip_safe=False,
      install_requires=['boto3','progress'])
