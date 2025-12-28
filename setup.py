from setuptools import setup, find_packages

setup(
    name="cdl-platform",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Add dependencies here if needed, 
        # but for now we focus on the entry point
    ],
    entry_points={
        "console_scripts": [
            "l4d=v1.l4_cli:main",
        ],
    },
)
