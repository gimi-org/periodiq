# setup.py
from setuptools import setup, find_packages

setup(
    name="django-periodiq",
    version="0.13.0",
    packages=find_packages(),
    install_requires=[
        "django~=3.2",
        "dramatiq>=1.16,<2.0",
        "pendulum>=3.0,<4.0",
    ],
)
