from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()

setup(
    name='lumos',
    version='0.0.3',
    author='DSDM - Institut De Recherches Servier',
    author_email='nicolas.boisseau@servier.com',
    license='NOLICENCE',
    description='A cell painting plateviewer',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/servier-github/jumpcp-aws',
    py_modules=['lumoscli', 'lumos'],
    packages=find_packages(),
    install_requires=[requirements],
    python_requires='>=3.8',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
    entry_points='''
        [console_scripts]
        lumos=lumoscli:cli
    '''
)
