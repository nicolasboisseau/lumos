# Lumos

Lumos is a first version of a python script to aggregate pictures obtained from cellpainting assay. This version of lumos fits with images generated with Yokogawa CV8000 High content analyis system.

Your images must be accessible from your filesystem.

## Setup
Create a virtualenv & activate it

    python -m venv venv
    source venv/bin/activate

Install depenencies & Install lumos

    pip install -r requirements.txt
    python setup.py install


## Use

From your prompt, launch help to see the arguments required.

    lumos --help
