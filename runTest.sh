# python_qgis and test variables like APP_ID needs to be defined in env.sh

[[ "$#" -lt 1 ]] && echo No test python file given.. && exit
py_args=$@
# ! [[ -e $py_args ]] && echo "No such file or directory: $py_args" && exit

! [[ -e ./env.sh ]] && echo env.sh is not found && exit
source ./env.sh

echo Running $py_args..
python_qgis $py_args
