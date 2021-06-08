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

+ `Load` : load data from an XYZ space into QGIS, given a valid token and server (PRD/CIT). To learn more about how to generate a token, refer to https://www.here.xyz/api/getting-token/ and https://xyz.api.here.com/token-ui/. 

    + `Mode`: there are 3 modes of loading
        + `Live loading`: interactively refresh features in tiles within the current canvas. Useful for visualization of dynamic dataset with full editing capabilities
        + `Incremental loading`: interactively refresh and cached features in tiles within the current canvas (no features delete). Useful for visualization and exploration of large dataset
        + `Static loading`: load and cache all features in space in background. Useful for importing and analysis of static dataset
    + `Chunk size` indicates the number of features per tile or iteration
    + `Layering` controls the organization of data in XYZ space into different QGIS layers based on fields similarity, with 3 levels:
        + `single`: merge data into 1 layer per geometry type
        + `maximal`: do not merge data, as many layers per geometry type
        + `balanced`: merge only similar data into 1 layer, balanced number of layers per geometry type

+ `Upload` : upload current Vector Layer to a new XYZ Hub space. For this to work, make sure that your token also has write-level permissions.

+ `Manage` : create new space, edit or delete existing space.

+ `Map Tile` : create HERE Map Tile layer given valid `app_id` and `app_code`. Alternatively, `api_key` can also be used.

+ `Settings` :

    + `Clear cache` : empty the temporary cache folder. Active layers will be invalid after clearing cache.

When the user make some edits to the loaded layer, the changes can be pushed to XYZ Hub via the button `Push changes` in the toolbar.

### Configure Server connection

Official Data Hub server is predefined under name "HERE Server" and thus is not required to be created. The following steps are only required for self-hosted Data Hub server and HERE Platform server.

1. From the "Web" menu in QGIS, select "XYZ Hub Connector" > "Add HERE Layer".
2. Press the "Setup" button and then "Setup Server" to add a new server. 
3. Click "Add" to add a new server.
4. Select server type

    a. Server Type: DATAHUB, enter "HERE self-hosted Data Hub" as the name and your Data Hub URL as the server.

    b. Server Type: PLATFORM, enter "HERE platform" as the name and PLATFORM_PRD as the server.

5. Click on OK to save the new server and OK again to return to the setup screen.

### Add HERE Data Hub Token

1. From the "Web" menu in QGIS, select "XYZ Hub Connector" > "Add HERE Layer".
2. Press the "Setup", ensure that "HERE Server" is selected in the Server drop down.
3. Click on "Add" to add your token.
4. Enter a name and corresponding Data Hub token created previously according to the guide https://www.here.xyz/api/getting-token/
5. Click on OK to save the token, and close the connection window

### Add HERE Platform Credentials

1. From the "Web" menu in QGIS, select "XYZ Hub Connector" > "Add HERE Layer".
2. Press the "Setup", ensure that "HERE Platform" is selected in the Server drop down.
3. Click on "Add" to add your credentials.
4. Enter "My credentials" as the name.
5. Select a credentials.properties containing your HERE Platform app credentials (typically location in `{USER_HOME}/.here/credentials.properties`
6. If you don't already have an app or a credentials.properties file then you can follow "platform credentials" section of this guide to create one: https://developer.here.com/documentation/java-scala-dev/dev_guide/topics/get-credentials.html
7. Grant access on the data to the HERE platform app so that it can access your project.  Do so by following this guide: https://developer.here.com/documentation/identity-access-management/dev_guide/topics/manage-projects.html
8. Click on OK to save the credentials, and close the connection window

### Load Your Data from HERE Platform

1. Create a new project (Project → New), save the project
2. From the "Web" menu in QGIS, select "XYZ Hub Connector" > "Add HERE Layer"
3. From the Connection drop down, select the "HERE Platform" connection and the "My Credentials" credentials that you created previously
4. Click "Connect"
5. Select one or more Interactive Map Layer entries
6. Click on "Load" to load the data

**Note:** You can also add background map tiles via the "Map Tile" tab. You will need to use your credentials from https://developer.here.com/.

## Testing

Test with unittest
```
./runTest.sh -m unittest test
```

Test with pytest-xdist
```
./runTest.sh -m pytest -n 2 test
```

## Development

1. Clone this repository.
2. Build the plugin by running `sh makeBuild.sh <VERSION NUMBER>`,
e.g. `sh makeBuild.sh 1.5.5`.

## Changelog
[CHANGELOG](CHANGELOG.md)
## License

Copyright (C) 2019-2021 HERE Europe B.V.

This project is licensed under the MIT license - see the [LICENSE](./LICENSE) file in the root of this project for license details.
