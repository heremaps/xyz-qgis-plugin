#!/usr/bin/env bash

set -ex

[[ "$#" -lt 1 ]] && echo No version given. Exiting.. && exit
ver=$1
folderSuffix=$2
# if [ "$#" -lt 1 ]; then
	# ver=dev
# else
	# ver=$1
# fi

mkdir -p build
rm -r build/*/ || true # delete folders only
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
patch_file=".github/01-oauthlib-bandit.patch"
if [ -e "$patch_file" ]; then
  echo "Applying patch '$patch_file' .."
  sed  -e "s|/XYZHubConnector|/build/XYZHubConnector|g" "$patch_file" | git apply -v -
fi
find build/XYZHubConnector -ipath '*/__pycache__' -type d | xargs rm -r

### Zip file

function update_metadata_and_zip() {
  (
  local ver=$1
  local folder=$2
  local folderSuffix=$3

  cd build

  if [ "$ver" ]; then
    sed -i"" -e "s/version=.*/version=$ver/" \
      ./$folder/metadata.txt
  fi
  if [ "$folderSuffix" ]; then
    sed -i"" -e "s/\(name=.*\)/\1 $folderSuffix/" \
      ./$folder/metadata.txt
  fi

  zip_name="$folder-$ver.zip"
  python ../zip_dir.py "$folder" "$zip_name"
  echo "Building completed: $zip_name"
  )
}

function rename_build_folder() {
  (
    local old_folder=$1
    local new_folder=$2
    cd build
    mv "$old_folder" "$new_folder"
  )
}

update_metadata_and_zip "$ver" "XYZHubConnector" ""

rename_build_folder "XYZHubConnector" "XYZHubConnector_DEV"
update_metadata_and_zip "$ver" "XYZHubConnector_DEV" "DEV"

if [[ -n "$folderSuffix" && "$folderSuffix" != "DEV" ]]; then
  rename_build_folder "XYZHubConnector_DEV" "XYZHubConnector_$folderSuffix"
  update_metadata_and_zip "$ver" "XYZHubConnector_$folderSuffix" "$folderSuffix"
fi
