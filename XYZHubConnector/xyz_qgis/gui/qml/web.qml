

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
    property string debugMode: ""

    // Create the initial browsing windows and open the startup page.
    Component.onCompleted: {
        saveLogFile(Qt.resolvedUrl("log.html"), loggingText)
    }

    function isDebug() {
        return debugMode != ""
    }

    function logText(txt) {
        loggingText += "<p>" + txt + "</p>"
    }

    function cbConsoleLog(level, message, lineNumber, sourceId) {
        let levels = ["INFO", "WARN", "ERROR"]
        logText(levels[level] + " - " + message + " - " + sourceId + ":" + lineNumber)
    }

    function saveLogFile(fileUrl, text) {
        if (!isDebug())
            return
        logText("saving log to " + fileUrl)
        var request = new XMLHttpRequest()
        request.open("PUT", fileUrl, false)
        request.send(text)
        return request.status
    }

    Connections {
        // not working
        target: windowParent
        Component.onDestruction: {
            saveLogFile(Qt.resolvedUrl("log.html"), loggingText)
        }
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

            // this.javaScriptConsoleMessage.connect(cbConsoleLog)
            // // show webview settings
            // logText("settings " + Object.keys(this.settings)
            // .filter((k) => typeof this.settings[k] != 'function')
            // .map((k) => "<br/> >>" + k + ": " + this.settings[k]).join(""))
            // this.settings.javascriptEnabled = true
        }

        onNewViewRequested: function (request) {
            let newWindow = windowComponent.createObject(windowParent)
            request.openIn(newWindow.webView)
        }

        onCertificateError: function (error) {
            logText("certificateError description: " + error.description + " error: " + error.error
                    + " overridable: " + error.overridable + "<br/> >> " + error.url)
            error.ignoreCertificateError() // ignore cert error
        }

        onLoadingChanged: {
            logText("loadRequest errorDomain: " + loadRequest.errorDomain
                    + " errorString: " + loadRequest.errorString + " status: "
                    + loadRequest.status + "<br/> >> " + loadRequest.url)

            if (loadRequest.status == WebEngineView.LoadStartedStatus) {
                return
            }

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
        title: webView.title

        property WebEngineView webView: {
            webViewComponent.createObject(this)
        }
    }
}
