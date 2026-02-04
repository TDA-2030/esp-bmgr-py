"""
Setup script for esp-bmgr-py package
"""
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from pathlib import Path
import sys
import site

# Read version from __init__.py
version = "0.1.0"
init_file = Path(__file__).parent / "esp_bmgr_py" / "__init__.py"
if init_file.exists():
    for line in init_file.read_text().splitlines():
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

# Read README if exists
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding='utf-8')


def _install_pth_file(site_packages_dir):
    """Helper function to install .pth file"""
    site_packages = Path(site_packages_dir)
    
    # Create .pth file that imports the injector module
    # .pth files must start with 'import' to execute code
    # The idf_injector module will monkey-patch idf.py to inject board manager extensions
    pth_content = """import esp_bmgr_py.idf_injector
"""
    
    # Write .pth file to site-packages
    pth_target = site_packages / "esp_bmgr_py.pth"
    pth_target.write_text(pth_content, encoding='utf-8')
    print(f"Installed .pth file to: {pth_target}")
    
    # Determine extension directory for info
    ext_dir = site_packages / "esp_bmgr_py"
    print(f"Extension directory: {ext_dir}")


class InstallWithPth(install):
    """Custom install command that installs .pth file to site-packages"""
    
    def run(self):
        # Run the standard install
        install.run(self)
        
        # Get site-packages directory
        if self.install_lib:
            site_packages = Path(self.install_lib)
        else:
            site_packages = Path(site.getsitepackages()[0])
        
        _install_pth_file(site_packages)


class DevelopWithPth(develop):
    """Custom develop command that installs .pth file to site-packages"""
    
    def run(self):
        # Run the standard develop
        develop.run(self)
        
        # Get site-packages directory
        site_packages = Path(site.getsitepackages()[0])
        
        _install_pth_file(site_packages)


setup(
    name="esp-bmgr-py",
    version=version,
    description="ESP Board Manager Python package for idf.py extensions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ESP Board Manager Team",
    url="https://github.com/espressif/esp-bmgr-py",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "pyyaml>=5.1",
    ],
    extras_require={
        "full": [
            "idf-component-manager",
        ],
    },
    cmdclass={
        'install': InstallWithPth,
        'develop': DevelopWithPth,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
