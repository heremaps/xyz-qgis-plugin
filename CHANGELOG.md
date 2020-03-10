# Changelog 

## Version 1.8.1 (2020-03-09)

#### Improvements

* Loading tile using web mercator projection
* Allow creating and editing space via json config (Advanced)

#### Bug Fixes

* Fix wrong data loaded from virtual space (here schema)

## Version 1.8.0 (2020-02-12)

#### New Feature

* 3 loading modes: 
    * Live loading: interactively refresh features in tiles 
    * Incremental loading: interactively refresh and cache features in tiles (no features delete)
    * Static loading: load and cache all features in space in background

#### Improvements

* Improve interactive loading mode behaviors:
    * Externally deleted features is refreshed and not cached in live loading #25
    * Editing mode temporarily stops interactive loading
    * Hiding layer temporarily stops interactive loading
    * Pushing changes to XYZ Hub to re-enable interactive loading
* Resume loading after open saved project or network interruption #22
* Save loader params into project
* Generate unique layer name

#### Bug Fixes

* Fix errors when delete layers or close project
    * Handle C++ wrapped object deleted error
    * Handle signalsBlocked, memory error
* Fix errors when importing XYZ layer from saved project
* Fix progress bar start and stop correctly
* Minimum zoom level is 1 (api, here schema)
    
## Version 1.7.6 (2019-11-28)

* Token manager: assigned name to token, add/edit/delete/ordering
* Stability improvement 
    * XYZ layer detection

## Version 1.7.5 (2019-11-08)

* bug fixes: import XYZ layer from saved project

## Version 1.7.4 (2019-09-11)

* bug fixes: updates in API 1.4

## Version 1.7.3 (2019-08-26)

* bug fixes: edit buffer, data upload

## Version 1.7.2 (2019-08-23)

* Tile loading mode, supports Live Map
    * A limited number of features per tile is reloaded every time panning or zooming occur.
    * XYZ Layer in tile loading mode works after open Saved project
* Layer categorization separates data in XYZ space based on fields similarity
    * single: merge data into 1 layer/geom
    * maximal: do not merge data, as many layers/geom
    * balanced: merge only similar data
* Similarity score [0-100] indicates the percentage of similar field
    * similarity threshold (higher = more layers; 0 means 1 layer/geometry)
* bug fixes: parser, fields similarity, case-different duplicate, dupe layer name

## Version 1.7.1 (2019-07-25)

* New: Features in space will be categorized according to geometry and properties
* 1 XYZ space might be loaded into multiple qgs vector layer in 1 group
* Property names will not be changed (except fid), ensure data consistency
* Handle case-different duplicate properties (e.g. name vs. Name)
* Handle special key properties (e.g. fid)
* No more promote geometry to multi-geom
* test parser, render layer
* Clear cache in menu
* Archive log file when it gets big (5MB)
* bug fixing

## Version 1.7.0 (2019-06-24)

* New: Changes of xyz layer can be pushed to XYZ Hub
* allow delete large number of features, overcome URL limit of 2000
* ignore null values when parsing feature to json
* refactor layer_utils, parser, render
* 2 variant of upload feature: modify and replace
* xyz layer added to top, basemap added to bottom
* finish message of controller is queued

## Version 1.6.2 (2019-05-27)

* fix compatibility issues with older setup (#15, #17, #18)
    * python 3, ver < 3.6
    * Qt5, ver < 5.8
* clickable url in error message box

## Version 1.6.1 (2019-05-07)

* fix several bugs in loading and uploading
    * unique field name (suffix ".number")
    * handle existing fid column in xyz space
    * when upload, ensure no fid, no metadata @ns, no dupe-id, no empty value
    * replace feature instead of modify properties of feature (upload)
    * each space is stored in 1 gpkg file that contains many geom layer
* add constraints in editing via UI (qml style)

## Version 1.6.0

* tab ui
* allow upload to existing layer
* fix error in NetworkFun
* fix bugs (#11, #10)

## Version 1.5.7

* fix bugs (unicode, feature count, etc.)
* use production server
* try to stop progress bar when error or close dialog
* update keywords in metadata

## Version 1.5.6

* add HERE map tile
* persistent config file across plugin Versions
* fix bugs with progress bar
* fix bugs not showing unicode char properly

## Version 1.5.5

* Support tag feature
* Handle mixed geometry space
* Bug fixes
* Show some error messages in dialog

## Version 1.5.3

* load space using iterate (adjusted to API 01.2019)
* bouding box loading under dev (ui disabled)
* authenticate using token, support PRD, CIT, SIT server
* display success/error message
* timeout for count request