#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

pip install -e .

cd hera_mc/tests
nosetests --with-coverage --cover-erase --cover-package=hera_mc --cover-html "$@"
