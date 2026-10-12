"""Setup script for library-manager."""
from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

setup(
    name="library-manager",
    version="1.0.0",
    author="Hardik Sankhla",
    author_email="datascientist.hardiksankhla@gmail.com",
    description="Personal offline library with Telegram cloud backup",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hardik-sankhla/library-manager",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    python_requires=">=3.10",
    install_requires=[
        "telethon>=1.45.0",
        "pyrogram>=2.0.106",
        "pymupdf>=1.28.2",
        "ebooklib>=0.20",
        "python-magic>=0.4.27",
        "Pillow>=11.0.0",
        "PyYAML>=6.0",
        "tqdm>=4.70.0",
        "rich>=13.0.0",
        "click>=8.1.0",
        "watchdog>=6.0.0",
        "xxhash>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "black>=24.0",
            "ruff>=0.4",
            "mypy>=1.10",
        ],
    },
    entry_points={
        "console_scripts": [
            "library-manager=library_manager.__main__:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)