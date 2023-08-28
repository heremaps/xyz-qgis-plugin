# HERE Maps for QGIS Plugin


HERE Maps for QGIS is a [QGIS](https://www.qgis.org) plugin which can be used to visualize, edit and analyze data from [Interactive Map Layers](https://developer.here.com/documentation/data-api/data_dev_guide/rest/layers.html#interactive-map-layers) (IML) on [HERE Platform](https://platform.here.com/) and from [HERE Data Hub](https://github.com/heremaps/xyz-hub) spaces directly on a map.

![new connection](res/new-connection.png)

## Installation

### Prerequisite

* QGIS version 3.0 or later

### Install via plugin repository in QGIS

1. In QGIS, navigate to menu **Plugins** > **Manage and Install Plugins...** > **All**
2. Search for `HERE Maps for QGIS` > **Install plugin**
3. Switch to tab **Installed**, make sure the plugin `HERE Maps for QGIS` is enabled.

### Install manually from zip file in QGIS

1. Download the [latest release](https://github.com/heremaps/xyz-qgis-plugin/releases) zip file
2. In QGIS, navigate to menu **Plugins** > **Manage and Install Plugins...** > **Install from ZIP**, then select the downloaded zip file.
3. Switch to tab **Installed**, make sure the plugin `HERE Maps for QGIS` is enabled.

## Usage

Once user have installed and enabled the plugin HERE Maps for QGIS, it can be accessed via the toolbar, or the menu **Web**. To use the plugin, user first need to create an account in [HERE Platform](https://platform.here.com/). Once done, user can try to login in the plugin either with the same HERE Platform user credential or with the app credential (in case the first option does not work).

### Login

#### Add User Credential

1. Ensure that `HERE Platform` is selected in the Server drop down.
2. If the User credential `HERE Platform User Login` exist in the Credential drop down, proceed directly to step 7
3. Click on `Add` to add your credential.
4. Tick the box `User login`
5. Enter "HERE Platform User Login" in the `Name`, user email in the `User email` and the realm from the Account confirmation email.
6. Click on OK to save the credential
7. Select the User credential and click `Connect` to login for the first time. The Platform login webpage will pop up.
8. Follow the steps in the Platform login webpage. Once login succesfully, the popup windows will be closed automatically and the list of available IML layers in your Platform account shall show up.

#### Add App Credential (optional)

1. Ensure that `HERE Platform` is selected in the Server drop down.
2. Click on `Add` to add your credential.
3. Enter "My App credential" as the name.
4. Select a `credentials.properties` containing your HERE Platform app credential (typically location in `{$HOME}/.here/credentials.properties`)
5. If user don't already have an app or a `credentials.properties` file then user can create one, following [the instructions here](https://developer.here.com/documentation/identity-access-management/dev_guide/topics/plat-token.html).
6. Grant access on the data to the HERE platform app so that it can access your project, following [the instructions here](https://developer.here.com/documentation/identity-access-management/dev_guide/topics/manage-projects.html).
7. Click on OK to save the credential, and close the connection window.
8. Click `Connect` to show the list of available IML layers.

#### Connect and list catalogs and layers

1. Select either the User credential or the App credential and click `Connect` 
2. The list of available IML layers in your Platform account shall show up in the tabular form
3. User use the search bar to find the catalogs and layers of interest

### Features

The main dialog contains 5 tabs:

+ `Load` : load data from a HERE Platform IML into QGIS, given a valid credential.

    + `Mode`: there are 3 modes of loading
        + `Live loading`: interactively refresh features in tiles within the current canvas. Useful for visualization of dynamic dataset with full editing capabilities
        + `Incremental loading`: interactively refresh and cached features in tiles within the current canvas (no features delete). Useful for visualization and exploration of large dataset
        + `Static loading`: load and cache all features in space in background. Useful for importing and analysis of static dataset

    + `Chunk size` indicates the number of features per tile or iteration. Default: 100. For large layer of point, lines features, value of 10000 is recommended. For large layer of polygon features, value of 1000 is recommended.

    + `Layering` controls the organization of data in XYZ space into different QGIS layers based on fields similarity, with 3 levels:
        + `single`: merge data into 1 layer per geometry type
        + `maximal`: do not merge data, as many layers per geometry type
        + `balanced`: merge only similar data into 1 layer, balanced number of layers per geometry type

+ `Upload` : upload current Vector Layer to a new XYZ Hub space. For this to work, make sure that your token also has write-level permissions.

+ `Manage` : create new space, edit or delete existing space.

+ `Map Tile` : create HERE Map Tile layer given valid `app_id` and `app_code`. Alternatively, `api_key` can also be used.

+ `Settings` :

    + `Clear cache` : empty the temporary cache folder. Active layers will be invalid after clearing cache.
    + `Clear cookies` : clear the login cookies. This could be helpful when login or loading show Authorization error

When the user make some edits to the loaded layer, the changes can be pushed to XYZ Hub via the button `Push changes` in the toolbar.

**Note:** User can also add background map tiles via the "Map Tile" tab. User will need to use your credential from https://developer.here.com/.

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

Copyright (C) 2019-2023 HERE Europe B.V.

This project is licensed under the MIT license - see the [LICENSE](./LICENSE) file in the root of this project for license details.
