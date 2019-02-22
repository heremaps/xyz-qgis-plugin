# xyz-qgis-plugin | XYZ Hub Connector

XYZ Hub Connector is a [QGIS](https://www.qgis.org) plugin that allows users to connect and to update data directly into [HERE XYZ Hub](https://www.here.xyz/). QGIS users can easily and quickly publish their work and analysis in vectorized format to the XYZ platform. Public and personal XYZ space data can be loaded into QGIS for further analysis and visualization.

## Installation

1. Install the following basic prerequisites:

   * QGIS version 3.0 or later
2. Download the [latest release](https://github.com/heremaps/xyz-qgis-plugin/releases) from GitHub as a single ZIP file, or build your own release following the instructions under [Development](#Development).
3. In QGIS, go to the menu **Plugins** > **Manage and Install plugins**, select tab **Install from ZIP**, then pick the above Zip file.
4. Switch to tab **Installed**, check if XYZ Hub Connector is enabled.

## Usage

Once you have installed and enabled the plugin XYZHubConnector, it can be accessed via the toolbar, or the menu **Web**

To load data from an XYZ space into QGIS, select menu `New Connection` provide a valid token and server (PRD/CIT). Check [this page](https://www.here.xyz/api/getting-token/) to learn more about how to generate a token if needed. The default token is a read-only token. Please use your own token with read/write access for more functionalities token can be generated on https://xyz.api.here.com/token-ui

To upload current Vector Layer to a new XYZ Hub space, select menu `Upload to a new XYZ Space` and fill in the details. For this to work, make sure that your token also has write-level permissions.

To empty the temporary cache folder, select Clear cache. Active layers will be invalid after clearing cache.


## Development

1. Clone this repository.
2. Build the plugin by running `makeBuild.sh <VERSION NUMBER>` e.g. `makeBuild.sh 1.5.5`.

## License

Copyright (C) 2019 HERE Europe B.V.

This project is licensed under the MIT license - see the [LICENSE](./LICENSE) file in the root of this project for license details.

