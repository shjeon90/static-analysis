from setuptools import setup, find_packages

packages = find_packages(include=["available_expressions_analysis", "available_expressions_analysis.*"])

setup(
    name="static_analysis",
    version="0.1.0",
    packages=packages,
    install_requires=[],
    author="shjeon",
    author_email="shjeon90@gachon.ac.kr",
    description="Static Analysis",
)