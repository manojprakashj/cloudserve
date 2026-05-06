#!/usr/bin/env python3
"""Setup script for CloudServe"""

from setuptools import setup, find_packages

setup(
    name="cloudserve",
    version="1.0.0",
    description="A better alternative to SimpleHTTPServer with Cloudflare tunnel support",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="CloudServe",
    python_requires=">=3.7",
    packages=find_packages(),
    include_package_data=True,
    package_data={"cloudserve": ["templates/*"]},
    install_requires=[
        "flask>=2.3.0",
        "werkzeug>=2.3.0",
    ],
    entry_points={
        "console_scripts": [
            "cloudserve=cloudserve:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
