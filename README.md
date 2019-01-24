# xyz-qgis-plugin | XYZ Hub Connector

XYZ Hub Connector is a QGIS plugin that allows users to connect and to update data directly into XYZ Hub. QGIS users can publish easily and quickly their work and analysis in vectorized format to XYZ Hub platform. Public and personal XYZ space can be loaded into QGIS for further analysis and visualization.

## Prerequisites

QGIS version 3+

## Installation

+ Zip the plugin folder XYZHubConnector (in the zip file should contain 1 folder XYZHubConnector)
+ In QGIS, menu **Plugins** > **Manage and Install plugins**, select tab **Install from ZIP**, then select the above Zip file
+ Switch to tab **Installed**, check if XYZ Hub Connector is enabled

## Usage

After the plugin XYZHubConnector is enabled, the functionalities can be accessed via the toolbar, or the menu **Web**

To load a XYZ space into QGIS, select menu New Connection given a valid Token and server (PRD/CIT)

To upload current Vector Layer to a new XYZ Hub space, select menu Upload to a new XYZ Space and fill in the details.

To empty the temporary cache folder, select Clear cache. Notice that the active layers will be invalid after clearing cache.

Note: The default token is a read-only token. Please use your own token with read/write access for more functionalities
Token can be generated here: https://xyz.api.here.com/token-ui

## Development

### Build the Zip file

Run the build script makeBuild.sh

### Test

On Windows platform

test single file
```
"C:/DEV/QGIS 3.0/bin/python-qgis.bat" xyz-qgis-plugin/test/test_controller.py -v > log.txt
```

test all folder (package)
```
"C:/DEV/QGIS 3.0/bin/python-qgis.bat" -m unittest -v

```