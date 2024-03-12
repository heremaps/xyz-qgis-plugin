# Release Notes

## Version 1.9.9 (2024-03-12)

🐛 FIXES 🐛

* Updated HERE Platform IML servers
* Set single layering mode as default
* Improved authorization
* Improved stability
* Deprecated HERE Data Hub servers
* Fixed OpenGL outdated driver error
* Show confirm dialog before installing dependencies

## Version 1.9.8 (2023-07-24)

🐛 FIXES 🐛
* Supports Here Platform login for MacOS
* Fixes issues with login and expired token
* Do not store Here Platform email and token into project files
* Fixes issue that some features are not displayed
* Improves UX and stability

## Version 1.9.7 (2023-05-12)

🐛 FIXES 🐛
* Fixed credential issues with Here Platform
* Used QtWebEngine and QML window instead of QtWebKit
* Applied one Here Platform credential to all layers, enabling easy switch between User and App credentials

⚡️ IMPROVEMENTS ⚡️
* Rename plugin, previously known as XYZ Hub Connector
* Display formatted JSON attribute
* Rename group/layer name in Layers panel, including Catalog and Layer name instead of layer id
* Remove non-mandatory field "Searchable properties" from "Manager layer" dialog

## Version 1.9.6 (2022-12-06)

🐛 FIXES 🐛
* Fixed error where some repaired layers are not displayed

## Version 1.9.5 (2022-10-18)

⚡️ IMPROVEMENTS ⚡️
* Automatically repairs HERE vector layers with invalid GeoPackage storage
* Handles Platform catalog with linked project in addition to home project

## Version 1.9.4 (2022-06-30)

🐛 FIXES 🐛
* Fixed crashes in QGIS 3.16

## Version 1.9.3 (2022-06-27)

⚡️ IMPROVEMENTS ⚡️
* Added search bar to query for space/layer
* Masked AppCode, ApiKey

🐛 FIXES 🐛
* Fixed layer ordering
* Handled layer without home project (HomeProjectNotFound error)

## Version 1.9.2 (2022-02-04)

🐛 FIXES 🐛
* Fixes platform realm not updated properly via UI

## Version 1.9.1 (2022-01-17)

⚡️ IMPROVEMENTS ⚡️
* Handles multiple Platform credentials and realms

🐛 FIXES 🐛
* Resolves "RuntimeError: wrapped C/C++ object of type has been deleted"
* Logs authentication error traceback

## Version 1.9.0 (2021-11-15)

✨ NEW FEATURES ✨
* Officially supports HERE Platform Interactive Map Layer (IML)
    * HERE Platform authentication via App credentials or Email login
    * Visualize and edit IML data
    * Manage IML layers: add/edit/delete layers

⚡️ IMPROVEMENTS ⚡️
* Improves editing delta layers
* Supports Z coordinates (elevation)

🐛 FIXES 🐛
* Prevents app crash when loading large geometries
* Does not convert string to integer when parsing feature
* Fixed vertex editor not working properly after loading
* Fixed ordering of vector layer when opening saved project
* Ensure xyz_id uniqueness via sqlite trigger instead of 'on replace conflict' constraint
* Ensure fields to be consistent with provider fields to prevent data corruption, especially after editing
* Ensure the paired order of fields-vector layer after a layer is removed (set fields to empty for deleted layer)
* Handle virtual fields (expression fields) in data loading
* Update test for parser and renderer
* Disconnect signal silently to avoid exception
* Fixed compatibility issues with QGIS 3.20
* Fixed overwritten layer properties when loading style
* Fixed dangling QgsFields of deleted layer
* Minor bug fixes

## Version 1.8.10 (2021-08-30)

⚡️ IMPROVEMENTS ⚡️
* Platform Layer Management: add/edit/delete layer
* Improves authentication error handling
* Minimizes the number of authentication requests

## Version 1.8.9 (2021-08-18)

✨ NEW FEATURES ✨
* Platform SSO user login

⚡️ IMPROVEMENTS ⚡️
* Get feature count for all IML layers

## Version 1.8.8 (2021-07-28)

⚡️ IMPROVEMENTS ⚡️
* Improves editing delta layers
* Supports Z coordinates

🐛 FIXES 🐛
* Do not convert string to integer when parsing feature
* Fixes vertex editor not working properly after loading
* Fixes ordering of vector layer when opening saved project

## Version 1.8.7 (2021-07-22)

🐛 FIXES 🐛
* Ensure fields to be consistent to prevent data corruption
* Handle virtual fields (expression fields) in data loading

## Version 1.8.6 (2021-07-14)

🐛 FIXES 🐛
* Fixes compatibility with QGIS 3.20
* Stability improvements

## Version 1.8.5 (2021-06-21)

🐛 FIXES 🐛
* Enable re-auth logic when uploading edited features to IML
* Minor bug fixes

## Version 1.8.4 (2021-06-08)

✨ NEW FEATURES ✨
* Supports HERE Platform Interactive Map Layers - IML (experimental)
* Enables loading, editing data in IML (experimental)

🐛 FIXES 🐛
* Minor bug fixes

## Version 1.8.3 (2021-02-08)

⚡️ IMPROVEMENTS ⚡️
* Updates HERE Tiles service URL

🐛 FIXES 🐛
* Handles nested properties when uploading data
* Fixes compatibility with QGIS 3.10, 3.16

## Version 1.8.2 (2020-06-10)

✨ NEW FEATURES ✨
* Supports self-hosted XYZ Hub Server: token authentication, loading, uploading, editing data, managing spaces
* Supports Property query and selection (XYZ Hub API)
* Supports Api Key for HERE Tiles

⚡️ IMPROVEMENTS ⚡️
* UX improvement
* Improved layer organization

## Version 1.8.1 (2020-03-10)

⚡️ IMPROVEMENTS ⚡️
* Loading tile using Web Mercator projection

🐛 FIXES 🐛
* Fixed wrong data loaded from virtual space, cf. https://www.here.xyz/cli/cli/#virtual-spaces

## Version 1.8.0 (2020-02-12)

✨ NEW FEATURES ✨
* Introducing three loading modes: 
    * Live loading - interactive mode for visualization of dynamic dataset with full editing capabilities
    * Incremental loading - interactive mode with caching for visualization and exploration of large dataset
    * Static loading - mode for importing and analysis of static dataset

⚡️ IMPROVEMENTS ⚡️
* Improve interactive loading mode behaviors
* Resume loading after open saved project or network interruption
* Save loader params into project
* Generate unique layer name

🐛 FIXES 🐛
* Fix errors when delete layers or close project
* Fix errors when opening project
* Fix progress bar behavior
