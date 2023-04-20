/**
 *
 * Copyright (c) 2023 HERE Europe B.V.
 *
 * SPDX-License-Identifier: MIT
 * License-Filename: LICENSE
 *
 */

function makeRequestSync(method, url, data) {
    var xhr = new XMLHttpRequest()
    xhr.open(method, url, false)

    if (method === 'POST') {
        xhr.setRequestHeader('Content-Type', 'application/json')
    }

    xhr.send(data)

    if (xhr.status >= 200 && xhr.status < 300) {
        return xhr.responseText
    } else {
        throw new Error(xhr.statusText)
    }
}

function hasTokenSync(baseUrl="https://platform.here.com") {
    try {
        var response = makeRequestSync(
                    "GET", baseUrl + "/api/portal/accessToken",
                    null)
        return {response: response}
    } catch (error) {
        return {error: error}
    }
}
