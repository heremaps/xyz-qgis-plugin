## Version 1.8.3 (2021-02-08)

⚡️ IMPROVEMENTS ⚡️
* Updates HERE Tiles

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
