import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="winunlock",
    version="0.1.0",  # Assuming this is version 0.1.0. Update as needed.
    author="Auto Actuary",  # Update with your name or organization name.
    description="A Python module that provides functionality for opening certain types of locked files in Windows.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/autoactuary/winunlock",  # Update with your repo URL.
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Update with the license you've chosen.
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.6",  # Adjusted to 3.6 for type hinting, but change as needed.
    use_scm_version={
        "write_to": "winunlock/version.py",
    },
    setup_requires=[
        "setuptools_scm",
    ],
    install_requires=[],
    package_data={
        "": [
            "py.typed",
        ],
    },
)
