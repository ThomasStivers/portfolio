import setuptools

with open("README.rst", "r", encoding="utf-8") as readme:
    long_description = readme.read()
version = {}
with open("portfolio/version.py", "r") as ver:
    exec(ver.read(), version)


setuptools.setup(
    name="portfolio-thomas.stivers",
    version=version["__version__"],
    author="Thomas Stivers",
    author_email="thomas.stivers@gmail.com",
    description="A package for managing financial portfolios.",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/thomas.stivers/portfolio",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "portfolio=app:main",
        ],
    },
)
