import setuptools

setuptools.setup(
    name = 'brutejudge',
    version = '0.2024.3.15',
    packages = setuptools.find_packages(),
    entry_points = {
        'console_scripts': ['brutejudge = brutejudge.__main__:_']
    }
)
