import Foundation

/// In-house usage logger — fire-and-forget POSTs to `/v1/events`.
/// Failures are swallowed so analytics never blocks the product flow.
enum AnalyticsEvent: String {
    case appOpen = "app_open"
    case linkSubmit = "link_submit"
    case fileUpload = "file_upload"
    case analyzeStart = "analyze_start"
    case analyzeComplete = "analyze_complete"
    case shootGuidanceView = "shoot_guidance_view"
    case clipUpload = "clip_upload"
    case remakeStart = "remake_start"
    case remakeComplete = "remake_complete"
    case exportShare = "export_share"
    case error = "error"
}

final class Analytics {
    static let shared = Analytics()

    var userId: String = "dev-user"
    var baseURL: URL = APIClient.baseURL

    private let session: URLSession
    private let encoder = JSONEncoder()
    private let queue = DispatchQueue(label: "com.videoart.analytics", qos: .utility)

    init(session: URLSession = .shared) {
        self.session = session
    }

    func track(
        _ event: AnalyticsEvent,
        jobId: String? = nil,
        metadata: [String: Any] = [:]
    ) {
        track(event.rawValue, jobId: jobId, metadata: metadata)
    }

    func track(
        _ eventName: String,
        jobId: String? = nil,
        metadata: [String: Any] = [:]
    ) {
        let uid = userId
        let base = baseURL
        queue.async { [weak self] in
            self?.send(eventName: eventName, userId: uid, jobId: jobId, metadata: metadata, base: base)
        }
    }

    private func send(
        eventName: String,
        userId: String,
        jobId: String?,
        metadata: [String: Any],
        base: URL
    ) {
        let url = base.appendingPathComponent("v1/events")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")
        request.timeoutInterval = 8

        var body: [String: Any] = [
            "event_name": eventName,
            "metadata": metadata,
        ]
        if let jobId {
            body["job_id"] = jobId
        }
        guard let data = try? JSONSerialization.data(withJSONObject: body) else { return }
        request.httpBody = data

        session.dataTask(with: request) { _, _, _ in
            // Intentionally ignore response / errors.
        }.resume()
    }
}
