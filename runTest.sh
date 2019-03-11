# python_qgis and test variables like APP_ID needs to be defined in env.sh

[[ "$#" -lt 1 ]] && echo No test python file given.. && exit
py=$1
! [[ -e $py ]] && echo "No such file or directory: $py" && exit

! [[ -e ./env.sh ]] && echo env.sh is not found && exit
source ./env.sh

echo Running $py..
python_qgis $py
