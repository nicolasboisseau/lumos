from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()
setup(
    name = 'lumos',
    version = '0.0.2',
    author = 'DSDM',
    author_email = '',
    license = 'NOLICENCE',
    description = 'A cell painting plateviewer',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/nicolasboisseau/lumos',
    py_modules = ['lumoscli','lumos'],
    packages = find_packages(),
    install_requires = [requirements],
    python_requires='>=3.8',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
    entry_points = '''
        [console_scripts]
        lumos=lumoscli:start
    '''
)