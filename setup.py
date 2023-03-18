from setuptools import setup

setup(name='pyawshelpers',
      version='0.1',
      description='Python helper classes and functions for AWS API',
      url='http://github.com/gmarchand/py-aws-helpers',
      author='Guillaume Marchand',
      author_email='contact@amazon.com',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.9'
      ],
      packages=['awshelpers'],
      zip_safe=False,
      install_requires=['boto3','progress'])
