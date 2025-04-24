from setuptools import setup, find_packages

setup(
    name='django-periodiq',
    version='0.13.0',
    description='A periodic task scheduler for Django using Dramatiq',
    url='https://github.com/gimi-org/periodiq',
    packages=find_packages(),
    install_requires=[
        'django>=3.2,<4.0',
        'dramatiq>=1.16,<2.0',
        'pendulum>=3.0,<4.0'
    ],
    classifiers=[
        'Framework :: Django',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
    ],
    python_requires='>=3.8',
)
