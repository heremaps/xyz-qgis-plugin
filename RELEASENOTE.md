# Release Notes

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
