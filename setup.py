from setuptools import setup, find_packages

setup(
    name="LOWER_PROJ_NAME",
    version="VERSION_NUMBER",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=PYTHON_VERSION",
    install_requires=[
    ],
)
