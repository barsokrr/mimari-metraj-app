import UIKit
import Capacitor
import Network

final class BridgeViewController: CAPBridgeViewController {
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "com.filemimarlik.metrajpro.network")
    private var isOfflineBannerVisible = false
    private var wasOfflineForReload = false
    private let offlineBanner = UILabel()
    private let nativeActionButton = UIButton(type: .system)

    override func viewDidLoad() {
        super.viewDidLoad()
        // Floating kontroller Streamlit alt düğmelerini kapatmasın (App Review boş / tıklanamaz UI).
        additionalSafeAreaInsets = UIEdgeInsets(top: 0, left: 0, bottom: 72, right: 0)
        setupPullToRefresh()
        setupNativeActionButton()
        setupOfflineBanner()
        startNetworkMonitor()
    }

    deinit {
        monitor.cancel()
    }

    private func setupPullToRefresh() {
        let refreshControl = UIRefreshControl()
        refreshControl.addTarget(self, action: #selector(refreshWebContent(_:)), for: .valueChanged)
        webView?.scrollView.refreshControl = refreshControl
    }

    @objc private func refreshWebContent(_ sender: UIRefreshControl) {
        let feedback = UIImpactFeedbackGenerator(style: .light)
        feedback.impactOccurred()
        webView?.reload()

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.7) {
            sender.endRefreshing()
        }
    }

    private func setupNativeActionButton() {
        nativeActionButton.setImage(UIImage(systemName: "ellipsis.circle.fill"), for: .normal)
        nativeActionButton.tintColor = .systemGreen
        nativeActionButton.backgroundColor = .white
        nativeActionButton.layer.cornerRadius = 24
        nativeActionButton.layer.shadowColor = UIColor.black.cgColor
        nativeActionButton.layer.shadowOffset = CGSize(width: 0, height: 2)
        nativeActionButton.layer.shadowOpacity = 0.2
        nativeActionButton.layer.shadowRadius = 4
        nativeActionButton.translatesAutoresizingMaskIntoConstraints = false
        nativeActionButton.addTarget(self, action: #selector(showNativeActions), for: .touchUpInside)

        view.addSubview(nativeActionButton)
        NSLayoutConstraint.activate([
            nativeActionButton.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -14),
            nativeActionButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -14),
            nativeActionButton.widthAnchor.constraint(equalToConstant: 48),
            nativeActionButton.heightAnchor.constraint(equalToConstant: 48)
        ])
    }

    @objc private func showNativeActions() {
        let feedback = UIImpactFeedbackGenerator(style: .medium)
        feedback.impactOccurred()

        let sheet = UIAlertController(title: "Hızlı işlemler", message: nil, preferredStyle: .actionSheet)
        sheet.addAction(UIAlertAction(title: "Yenile", style: .default) { [weak self] _ in
            self?.webView?.reload()
        })
        sheet.addAction(UIAlertAction(title: "Bağlantıyı paylaş", style: .default) { [weak self] _ in
            self?.shareAppLink()
        })
        sheet.addAction(UIAlertAction(title: "Vazgeç", style: .cancel))

        if let popover = sheet.popoverPresentationController {
            popover.sourceView = nativeActionButton
            popover.sourceRect = nativeActionButton.bounds
        }

        present(sheet, animated: true)
    }

    private func shareAppLink() {
        let appURL = URL(string: "https://mimari-metraj-app.streamlit.app")!
        let activity = UIActivityViewController(activityItems: [appURL], applicationActivities: nil)
        if let popover = activity.popoverPresentationController {
            popover.sourceView = nativeActionButton
            popover.sourceRect = nativeActionButton.bounds
        }
        present(activity, animated: true)
    }

    private func setupOfflineBanner() {
        offlineBanner.text = "İnternet bağlantısı yok. Ağınızı kontrol edin."
        offlineBanner.textAlignment = .center
        offlineBanner.backgroundColor = UIColor.systemRed.withAlphaComponent(0.95)
        offlineBanner.textColor = .white
        offlineBanner.font = UIFont.systemFont(ofSize: 13, weight: .semibold)
        offlineBanner.numberOfLines = 2
        offlineBanner.isHidden = true
        offlineBanner.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(offlineBanner)
        NSLayoutConstraint.activate([
            offlineBanner.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            offlineBanner.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            offlineBanner.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            offlineBanner.heightAnchor.constraint(greaterThanOrEqualToConstant: 36)
        ])
    }

    private func startNetworkMonitor() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if path.status == .satisfied {
                    self.hideOfflineBannerAndReloadIfNeeded()
                } else {
                    self.showOfflineBanner()
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }

    private func showOfflineBanner() {
        if isOfflineBannerVisible {
            return
        }
        wasOfflineForReload = true
        isOfflineBannerVisible = true
        offlineBanner.alpha = 0
        offlineBanner.isHidden = false
        UIView.animate(withDuration: 0.25) {
            self.offlineBanner.alpha = 1
        }
    }

    private func hideOfflineBannerAndReloadIfNeeded() {
        if !isOfflineBannerVisible {
            return
        }
        isOfflineBannerVisible = false
        UIView.animate(withDuration: 0.25, animations: {
            self.offlineBanner.alpha = 0
        }) { _ in
            self.offlineBanner.isHidden = true
        }
        if wasOfflineForReload {
            wasOfflineForReload = false
            webView?.reload()
        }
    }
}
