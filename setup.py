from setuptools import setup, find_packages

with open("euro_website/__init__.py", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"')
            break
    else:
        version = "0.0.0"

setup(
    name="euro_website",
    version=version,
    description="Euro Plast public website for ERPNext",
    author="Euro Plast",
    author_email="hello@example.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
