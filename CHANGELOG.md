# Changelog 

## version 1.6.2 (2019-05-27)

* fix compatibility issues with older setup (#15, #17, #18)
    * python 3, ver < 3.6
    * Qt5, ver < 5.8
* clickable url in error message box

## version 1.6.1 (2019-05-07)

* fix several bugs in loading and uploading
    * unique field name (suffix ".number")
    * handle existing fid column in xyz space
    * when upload, ensure no fid, no metadata @ns, no dupe-id, no empty value
    * replace feature instead of modify properties of feature (upload)
    * each space is stored in 1 gpkg file that contains many geom layer
* add constraints in editing via UI (qml style)

## version 1.6.0

* tab ui
* allow upload to existing layer
* fix error in NetworkFun
* fix bugs (#11, #10)

## version 1.5.7

* fix bugs (unicode, feature count, etc.)
* use production server
* try to stop progress bar when error or close dialog
* update keywords in metadata

## version 1.5.6

* add HERE map tile
* persistent config file across plugin versions
* fix bugs with progress bar
* fix bugs not showing unicode char properly

## version 1.5.5

* Support tag feature
* Handle mixed geometry space
* Bug fixes
* Show some error messages in dialog

## version 1.5.3

* load space using iterate (adjusted to API 01.2019)
* bouding box loading under dev (ui disabled)
* authenticate using token, support PRD, CIT, SIT server
* display success/error message
* timeout for count request