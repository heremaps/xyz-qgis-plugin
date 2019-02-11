[[ "$#" -lt 1 ]] && echo No version given. Exiting.. && exit
ver=$1
# if [ "$#" -lt 1 ]; then
	# ver=dev
# else
	# ver=$1
# fi

mkdir build 
rm -r build/*
# lst=$(git ls-files XYZHubConnector | grep -v '/\.')
# lst=$(git ls-tree --name-only -r master XYZHubConnector | grep -v '/\.') # input files is staged in git (master)
lst=$(git ls-tree --name-only -r HEAD XYZHubConnector | grep -v '/\.') # input files is staged in git HEAD
for f in $lst ; do
 echo $f 
 git --work-tree=build checkout HEAD -- $f # checkout from git instead of copy current local files
done
# cp --parents $lst build # copy current local files

### Zip file
# cd build && zip -q -r QGIS-XYZ-Plugin-$ver.zip XYZHubConnector
cd build && python ../zip_dir.py XYZHubConnector QGIS-XYZ-Plugin-$ver.zip
cd ..