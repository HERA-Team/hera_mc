set -xe

# want 1 script to rule them all
# but this part is not needed on MACOS
if [[ ! $OS == 'macos-latest' ]]; then
  if [ ! -z "$WITH_SUDO" ]; then
    sudo apt-get update
    sudo apt-get install -y gcc g++ curl libpq-dev postgresql-client
  else
    apt-get update
    apt-get install -y gcc g++ curl libpq-dev postgresql-client
  fi
fi
conda config --set always_yes yes --set changeps1 no
conda update -q conda
conda info -a
conda create --name=${ENV_NAME}  python=$PYTHON --quiet

if [[ $PYTHON == 2.7 ]]; then
  conda env update -n ${ENV_NAME} -f ci/${ENV_NAME}_py2.yaml
else
  conda env update -n ${ENV_NAME} -f ci/${ENV_NAME}.yaml
fi

source activate ${ENV_NAME}
conda list -n ${ENV_NAME}


# check that the python version matches the desired one; exit immediately if not
PYVER=`python -c "import sys; print('{:d}.{:d}'.format(sys.version_info.major, sys.version_info.minor))"`
if [[ $PYVER != $PYTHON ]]; then
  exit 1;
fi
