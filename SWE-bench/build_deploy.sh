# !bin/bash

python3 -m build

python3 -m twine upload --skip-existing --repository pypi dist/*
# python3 -m twine upload --skip-existing --repository testpypi dist/*