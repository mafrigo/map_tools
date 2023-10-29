from setuptools import setup


setup(
    name="map_tools",
    version="0.1",
    packages=['map_tools'],
    install_requires=[
        "numpy",
        "matplotlib>=3.6.3",
        "pyyaml",
        "cartopy",
        "pathlib"
    ],
    package_data={'map_tools': ['map_tools/config.yaml']},
    include_package_data=True,
)