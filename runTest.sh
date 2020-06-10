#!/bin/bash

# python_qgis and test variables like APP_ID needs to be defined in ./env

[ "$#" -lt 1 ] && echo No test python file given.. && exit
py_args=$@
# ! [ -e $py_args ] && echo "No such file or directory: $py_args" && exit

! [ -e ./.env ] && echo .env is not found && exit
. ./.env

echo Running $py_args..
"$PYTHON_QGIS" $py_args
