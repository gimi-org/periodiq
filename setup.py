from setuptools import setup, find_packages

setup(
    name="django-periodiq",
    version="0.13.0",
    description="Cron-like scheduling for Django using Dramatiq",
    packages=find_packages(),
    install_requires=[
        "django>=3.2,<4.0",
        "dramatiq>=1.16,<2.0",
        "pendulum>=3.0,<4.0",
    ],
    include_package_data=True,
    zip_safe=False,
)
