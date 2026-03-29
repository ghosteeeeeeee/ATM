from setuptools import setup, find_packages

setup(
    name="litellm-ride",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "litellm-ride=litellm_ride.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
