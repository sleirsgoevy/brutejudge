import setuptools

setuptools.setup(
    name = 'brutejudge',
    version = '0.2023.10.28.1',
    packages = setuptools.find_packages(),
    entry_points = {
        'console_scripts': ['brutejudge = brutejudge.__main__:_']
    }
)
