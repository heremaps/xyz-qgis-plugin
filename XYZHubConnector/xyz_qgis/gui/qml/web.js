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

//debugConsole(txt) {
//    console.log(txt)
//}
//
//attemptRefreshToken(baseUrl="https://platform.here.com") {
//    debugConsole('Inside attemptRefreshToken()');
//    // Start timeout to catch silent Auth failure
//    startAttemptingRefreshTokenTimeout();
//
//    //Create hidden iframe of page that calls service.refreshToken
//
//    const refreshIframe = document.createElement('iframe');
//    const iFrameSrc = baseUrl + "/refreshToken";
//
//    refreshIframe.src = iFrameSrc;
//    refreshIframe.setAttribute('id', 'refresh-access-token');
//    refreshIframe.setAttribute('style', 'display:none; visibility:hidden;');
//    refreshIframe.setAttribute('loading', 'lazy');
//
//    debugConsole('adding iframe with src=', iFrameSrc);
//    document.body.appendChild(refreshIframe);
//
//    const iFrameEventPromise = new Promise(resolve => {
//      window.addEventListener('message', function processMessage(e) {
//        console.debug('event received from iframe', e);
//        if (e.origin !== new URL(window.location.href).origin) {
//          console.debug('origins did not match');
//          resolve(null);
//        }
//
//        if (e.data.message === 'refreshAccessToken') {
//          // Remove iframe from DOM
//          console.debug('removing iframe');
//          const iframeToClose = document.getElementById('refresh-access-token');
//
//          if (iframeToClose) {
//            iframeToClose.remove();
//          }
//
//          // Remove listener
//          window.removeEventListener('message', processMessage);
//
//          // Handle message
//          if (e.data.accessToken) {
//            console.debug('received new accessToken from iframe data');
//            resolve(e.data);
//          }
//          resolve(null);
//        }
//      });
//    })
//      .then(response => {
//        debugConsole('calling stop attempt token refresh timeout');
//        this.stopAttemptingRefreshTokenTimeout();
//        if (response) {
//          const accessTokenResponse = {
//            accessToken: response.accessToken,
//            accessTokenExpires: response.accessTokenExpires,
//            refreshTokenExpires: response.refreshTokenExpires
//          };
//          //
//          this.handleAccessTokenSuccess(accessTokenResponse);
//
//          return this.handleRefreshTokenSuccess(accessTokenResponse);
//        }
//        //eslint-disable-next-line
//        throw ('error with refreshing token iframe sent the response: ', response);
//      })
//      .catch(error => this.handleHAError(error));
//
//    return iFrameEventPromise;
//  }
//
//
//startAttemptingRefreshTokenTimeout() {
//    console.debug('Attempting token refresh Timeout ');
//
//    if (this.timer) {
//      console.debug('Attempted to start attempt refresh token timeout, but it is already in progress.');
//      return;
//    }
//
//    this.timer = setTimeout(() => {
//      // If we don't hear back from a successful refresh after the refreshTokenFailureTimeout time, handle passive auth failure
//      this.handlePassiveAuthIntervalFailure();
//      console.debug(
//        `pass auth interval failure, timing out in ${this.hereAccountWebApiOptions.refreshTokenFailureTimeout} seconds`
//      );
//    }, this.hereAccountWebApiOptions.refreshTokenFailureTimeout * 1000);
//    debugConsole(
//      `setting timeout for ${this.hereAccountWebApiOptions.refreshTokenFailureTimeout} sec, timerId==`,
//      this.timer
//    );
//  }
//
//  stopAttemptingRefreshTokenTimeout() {
//    this.debugConsole('inside stopAttemptingRefreshTokenTimeout() and timerId==', this.timer);
//    if (this.timer) {
//      console.debug('stopping to attempt token refresh timeout');
//      clearTimeout(this.timer);
//      this.timer = null;
//    }
//  }

