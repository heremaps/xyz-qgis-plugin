[[ "$#" -lt 1 ]] && echo No version given. Exiting.. && exit
ver=$1
# if [ "$#" -lt 1 ]; then
	# ver=dev
# else
	# ver=$1
# fi

mkdir -p build
rm -r build/*/ # delete folders only
# lst=$(git ls-files XYZHubConnector | grep -v '/\.') # input files are all files in XYZHubConnector folder
# lst=$(git ls-tree --name-only -r master XYZHubConnector | grep -v '/\.') # input files is staged in git (master)
lst=$(git ls-tree --name-only -r HEAD XYZHubConnector | grep -v '/\.') # input files is staged in git HEAD
for f in $lst ; do
 echo $f
 git --work-tree=build checkout HEAD -- $f # checkout from git instead of copy current local files
done
# cp --parents $lst build # copy current local files

## Install lib
pip install -r requirements.txt -t build/XYZHubConnector/external
find build/XYZHubConnector -ipath '*/__pycache__' -type d | xargs rm -r

### Zip file
# cd build && zip -q -r QGIS-XYZ-Plugin-$ver.zip XYZHubConnector
if $( echo $ver | grep -q alpha ); then
  (
  cd build
  mv XYZHubConnector XYZHubConnector_alpha
  sed -i -e 's/name=.*/name=XYZ Hub Connector alpha/' \
    -e "s/version=.*/version=$ver/" \
    ./XYZHubConnector_alpha/metadata.txt
  python ../zip_dir.py XYZHubConnector_alpha QGIS-XYZ-Plugin-$ver.zip
  )
else
  (
  cd build && python ../zip_dir.py XYZHubConnector QGIS-XYZ-Plugin-$ver.zip
  )
fi