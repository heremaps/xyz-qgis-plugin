# XYZ Hub Connector - QGIS plugin


XYZ Hub Connector is a [QGIS](https://www.qgis.org) plugin that allows users to connect and to update data directly into [HERE XYZ Hub](https://www.here.xyz/). QGIS users can easily and quickly publish their work and analysis in vectorized format to the XYZ platform. Public and personal XYZ space data can be loaded into QGIS for further analysis and visualization.

![new connection](res/new-connection.png)

## Installation

### Prerequisite

* QGIS version 3.0 or later

### Install via plugin repository in QGIS

1. In QGIS, navigate to menu **Plugins** > **Manage and Install Plugins...** > **All**
2. Search for `XYZ Hub Connector` > **Install plugin**
3. Switch to tab **Installed**, make sure the plugin `XYZ Hub Connector` is enabled.

### Install manually from zip file in QGIS

1. Download the [latest release](https://github.com/heremaps/xyz-qgis-plugin/releases) zip file
2. In QGIS, navigate to menu **Plugins** > **Manage and Install Plugins...** > **Install from ZIP**, then select the downloaded zip file.
3. Switch to tab **Installed**, make sure the plugin `XYZ Hub Connector` is enabled.

## Usage

Once you have installed and enabled the plugin XYZ Hub Connector in QGIS, it can be accessed via the toolbar, or the menu **Web**. The main dialog contains 5 tabs:

+ `Load` : load data from an XYZ space into QGIS, given a valid token and server (PRD/CIT). To learn more about how to generate a token, refer to https://www.here.xyz/api/getting-token/ and https://xyz.api.here.com/token-ui/. There are 2 modes of loading, `Tile loading` (default) and `Iterate loading`. 
    + `Tile loading` loads the data in the current bounding box interactively everytime the user moves around the map, suitable for visualization of large spaces. `Chunk size` indicates the number of features per tile.
    + The other mode `Iterate loading` tries to load all data available in the given XYZ space iteratively, suitable for visualization of small spaces. `Chunk size` indicates the number of features per iteration.
    + `Layer categorization` controls the organization of data in XYZ space into different QGIS layers based on fields similarity, with 3 levels:
        + `single`: merge data into 1 layer per geometry type
        + `maximal`: do not merge data, as many layers per geometry type
        + `balanced`: merge only similar data into 1 layer, balanced number of layers per geometry type

+ `Upload` : upload current Vector Layer to a new XYZ Hub space. For this to work, make sure that your token also has write-level permissions.

+ `Manage` : create new space, edit or delete existing space.

+ `Map Tile` : create HERE Map Tile layer given valid `app_id` and `app_code`.

+ `Settings` :

    + `Clear cache` : empty the temporary cache folder. Active layers will be invalid after clearing cache.

When the user make some edits to the loaded layer, the changes can be pushed to XYZ Hub via the button `Push changes` in the toolbar.

## Development

1. Clone this repository.
2. Build the plugin by running `sh makeBuild.sh <VERSION NUMBER>`,
e.g. `sh makeBuild.sh 1.5.5`.

## Changelog
[CHANGELOG](CHANGELOG.md)
## License

Copyright (C) 2019 HERE Europe B.V.

This project is licensed under the MIT license - see the [LICENSE](./LICENSE) file in the root of this project for license details.
