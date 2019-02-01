# xyz-qgis-plugin | XYZ Hub Connector

XYZ Hub Connector is a QGIS plugin that allows users to connect and to update data directly into [HERE XYZ Hub](https://www.here.xyz/). QGIS users can easily and quickly publish their work and analysis in vectorized format to the XYZ platform. Public and personal XYZ space data can be loaded into QGIS for further analysis and visualization.

## Prerequisites

QGIS version 3+

## Installation

+ Zip the plugin folder XYZHubConnector (the zip file should contain 1 folder called `XYZHubConnector`)
+ In QGIS, go to the menu **Plugins** > **Manage and Install plugins**, select tab **Install from ZIP**, then pick the above Zip file
+ Switch to tab **Installed**, check if XYZ Hub Connector is enabled

## Usage

After the plugin XYZHubConnector is enabled it can be accessed via the toolbar, or the menu **Web**

To load data from an XYZ space into QGIS, select menu `New Connection` provide a valid token and server (PRD/CIT). Check [this page](https://www.here.xyz/api/getting-token/) to learn more about how to generate a token if needed. The default token is a read-only token. Please use your own token with read/write access for more functionalities token can be generated here: https://xyz.api.here.com/token-ui


To upload current Vector Layer to a new XYZ Hub space, select menu `Upload to a new XYZ Space` and fill in the details. For this to work, make sure that your token also has write-level permissions.

To empty the temporary cache folder, select Clear cache. Active layers will be invalid after clearing cache.


## Development

### Build the Zip file

Run the build script `makeBuild.sh`

### Test

On Windows platforms

test single file
```
"C:/DEV/QGIS 3.0/bin/python-qgis.bat" xyz-qgis-plugin/test/test_controller.py -v > log.txt
```

test all folder (package)
```
"C:/DEV/QGIS 3.0/bin/python-qgis.bat" -m unittest -v

```
