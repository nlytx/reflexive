import setuptools

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "reflexive",
    version = "0.1.1",
    author = "Andrew Gibson",
    author_email = "andrew@nlytx.io",
    description = "Supports AWS Reflexive Expressions Analysis",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/nlytx/reflexive",
    project_urls = {
        "Bug Tracker": "https://github.com/nlytx/reflexive/issues",
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where="src"),
    python_requires = ">=3.10"
)