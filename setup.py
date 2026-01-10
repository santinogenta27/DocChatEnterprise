"""Setup script for DocChatEnterprise package."""

from setuptools import setup, find_packages
from pathlib import Path

# Leer README si existe
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

# Leer requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="docchat-enterprise",
    version="1.0.0",
    description="Enterprise Data AI - Multi-Agent RAG with Autonomous Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DocChatEnterprise Team",
    packages=find_packages(exclude=["tests", "tests.*", "*.tests", "*.tests.*"]),
    install_requires=requirements,
    python_requires=">=3.12",
    include_package_data=True,
    zip_safe=False,
)

