#!/bin/bash

# python_qgis and test variables like APP_ID needs to be defined in ./env

[ "$#" -lt 1 ] && echo No test python file given. Try running with argument: -m unittest -v test.test_case && exit
py_args=$@
# ! [ -e $py_args ] && echo "No such file or directory: $py_args" && exit

if [ -e ./.env ]
then
  echo .env detected, injecting variable..
  . ./.env
else
  echo .env not found, please inject variable beforehand
fi

# headless mode
export QT_QPA_PLATFORM=offscreen

CURRENT_DIR="$(pwd)"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"
echo Running $py_args..
"$PYTHON_QGIS" $py_args; cd "$CURRENT_DIR"
