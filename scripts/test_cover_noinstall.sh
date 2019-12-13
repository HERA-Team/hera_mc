#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

cd hera_mc/tests
python -m pytest --cov=hera_mc --cov-config=.coveragerc \
       --cov-report term --cov-report html:cover \
       "$@"
