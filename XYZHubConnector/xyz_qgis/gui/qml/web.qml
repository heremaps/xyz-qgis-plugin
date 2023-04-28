/**
 *
 * Copyright (c) 2023 HERE Europe B.V.
 *
 * SPDX-License-Identifier: MIT
 * License-Filename: LICENSE
 *
 */


import QtQuick 2.10
import QtQuick.Window 2.10
import QtQml 2.10
import QtWebEngine 1.3
import QtQuick.Layouts 1.10

// https://doc.qt.io/qt-5/qml-qtwebengine-webengineview.html#newViewRequested-signal
Item {
    id: windowParent

    property string tokenJson: ""
    property string error: ""
    property string loggingText: ""

    property string loginUrl: "https://platform.here.com"
    property int initialWidth: 600
    property int initialHeight: 600
    width: initialWidth
    height: initialHeight
    //    property var debugWindow: debugWindowComponent.createObject(windowParent)

    // Create the initial browsing windows and open the startup page.
    Component.onCompleted: {

        // debug
        //let debugWindow = debugWindowComponent.createObject(windowParent)
    }

    function logText(txt) {
        loggingText += "<p>" + txt + "</p>"
    }

    function getToken() {
        return tokenJson
    }

    function getError() {
        return error
    }

    function handleOutput(output) {
        function saveToken(response) {
            logText(response)
            logText(JSON.parse(response).accessToken)
            tokenJson = response
        }
        function saveError(err) {
            logText(err)
            error = err
        }

        if (output.response) {
            saveToken(output.response)
        }
        if (output.error) {
            saveError(output.error)
        }
    }

    function closeWindow(item) {
        item.Window.window.close()
    }

    function runCheckToken() {
        // logText("run script")
        function handleOutputAndClose(output) {
            handleOutput(output)
            closeWindow(windowParent)
        }

        // close window after get token
        webView.runJavaScript('let url="' + loginUrl + '"; hasTokenSync(url);',
                              handleOutputAndClose)
    }

    property WebEngineView webView: webViewComponent.createObject(windowParent,
                                                                  {
                                                                      "url": loginUrl,
                                                                      "userScripts": [script_]
                                                                  })
    WebEngineProfile {
        id: profile_
    }
    WebEngineScript {
        id: script_
        injectionPoint: WebEngineScript.DocumentReady
        worldId: WebEngineScript.MainWorld
        sourceUrl: "web.js"
    }
    property Component webViewComponent: WebEngineView {
        anchors.fill: parent

        profile: profile_ // use new cookies everytime
        Component.onCompleted: {

        }

        onNewViewRequested: function (request) {
            let newWindow = windowComponent.createObject(windowParent)
            request.openIn(newWindow.webView)
        }

        onLoadingChanged: {
            if (loadRequest.status == WebEngineView.LoadStartedStatus) {
                return
            }
            logText(loadRequest.url.toString().length + " " + loadRequest.url)

            let url1 = loadRequest.url.toString().replace(/\/$/, "")
            let url2 = loginUrl.replace(/\/$/, "")

            if (url1 === url2) {
                runCheckToken()
            }
        }

        onWindowCloseRequested: {
            closeWindow(this)
        }
    }

    property Component windowComponent: Window {
        // Destroy on close to release the Window's QML resources.
        // Because it was created with a parent, it won't be garbage-collected.
        onClosing: destroy()
        visible: true
        width: initialWidth
        height: initialHeight

        property WebEngineView webView: {
            webViewComponent.createObject(this)
        }
    }

    property Component debugWindowComponent: Window {
        // Destroy on close to release the Window's QML resources.
        // Because it was created with a parent, it won't be garbage-collected.
        onClosing: destroy()
        visible: true
        width: initialWidth
        height: initialHeight
        modality: Qt.WindowModal
        title: "Debug"

        ColumnLayout {
            TextEdit {
                text: "token: " + tokenJson
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                textFormat: TextEdit.AutoText
                height: 100
            }
            TextEdit {
                text: loggingText
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                textFormat: TextEdit.AutoText
                height: 100
            }
        }
    }
}
