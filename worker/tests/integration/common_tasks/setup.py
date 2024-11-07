from setuptools import setup

setup(name='common_tasks',
      version='0.0.0',
      description='A girder_worker extension with common tasks for testing',
      author='Kitware Inc.',
      author_email='kitware@kitware.com',
      license='Apache v2',
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: Apache Software License'
          'Natural Language :: English',
          'Programming Language :: Python'
      ],
      entry_points={
          'girder_worker_plugins': [
              'common_tasks = common_tasks:CommonTasksPlugin',
          ]
      },
      install_requires=[
          'girder_worker'
      ],
      packages=['common_tasks'],
      zip_safe=False)
