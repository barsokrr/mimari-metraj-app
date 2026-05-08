import Foundation
import ObjectiveC
import UIKit
import WebKit
import Capacitor

/// Capacitor's `WebViewDelegationHandler` routes `window.open` / new-window navigations through
/// `UIApplication.shared.open`, which leaves the app (Safari). App Review flags that for sign-in flows.
///
/// We only swizzle **`createWebViewWith`** so popups load in the **same WKWebView**. We intentionally do **not**
/// replace `decidePolicyFor`: a custom policy hook can cancel navigations (e.g. `about:blank`, redirects) and cause a
/// blank screen (Guideline 2.1).
enum CapacitorInAppNavigationHook {
    private static var didInstall = false

    static func installIfNeeded() {
        guard !didInstall else { return }
        didInstall = true

        let cls = WebViewDelegationHandler.self

        let createOriginal = NSSelectorFromString("webView:createWebViewWithConfiguration:forNavigationAction:windowFeatures:")
        let createReplacement = #selector(WebViewDelegationHandler.metraj_cap_hook_createWebView(_:createWebViewWith:for:windowFeatures:))

        guard let mCreateOrig = class_getInstanceMethod(cls, createOriginal),
              let mCreateNew = class_getInstanceMethod(cls, createReplacement) else {
            return
        }
        method_exchangeImplementations(mCreateOrig, mCreateNew)
    }
}

extension WebViewDelegationHandler {

    @objc func metraj_cap_hook_createWebView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        guard let url = navigationAction.request.url else {
            return nil
        }

        let scheme = url.scheme?.lowercased() ?? ""
        // Some providers open an intermediate about:blank window first.
        // Loading that into the main WKWebView can leave the app on a white screen.
        if scheme == "about" || scheme == "javascript" || url.absoluteString.lowercased() == "about:blank" {
            return nil
        }

        switch scheme {
        case "http", "https":
            webView.load(navigationAction.request)
        case "mailto", "tel", "sms":
            if UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url, options: [:], completionHandler: nil)
            }
        default:
            webView.load(navigationAction.request)
        }
        return nil
    }
}
