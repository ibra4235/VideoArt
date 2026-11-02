import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case http(Int, String)
    case decoding(Error)
    case emptyResponse

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Geçersiz API adresi"
        case .http(let code, let body):
            return "Sunucu hatası (\(code)): \(body)"
        case .decoding(let err):
            return "Yanıt okunamadı: \(err.localizedDescription)"
        case .emptyResponse:
            return "Boş yanıt"
        }
    }
}

final class APIClient {
    /// Simulator → Mac host. Fiziksel cihazda Mac'in LAN IP'sini yaz.
    static var baseURL = URL(string: "http://127.0.0.1:8000")!

    /// Stub auth — Sign in with Apple bu dilimde yok.
    var userId: String = "dev-user"

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(session: URLSession = .shared) {
        self.session = session
        self.decoder = JSONDecoder()
        self.encoder = JSONEncoder()
    }

    func health() async throws -> [String: Any] {
        let url = Self.baseURL.appendingPathComponent("health")
        let (data, response) = try await session.data(from: url)
        try Self.throwIfNeeded(response, data: data)
        let obj = try JSONSerialization.jsonObject(with: data)
        return obj as? [String: Any] ?? [:]
    }

    func uploadAnalyze(fileURL: URL) async throws -> JobCreateResponse {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/analyze")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let filename = fileURL.lastPathComponent
        let fileData = try Data(contentsOf: fileURL)
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n"
                .data(using: .utf8)!
        )
        body.append("Content-Type: video/mp4\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        try Self.throwIfNeeded(response, data: data)
        do {
            return try decoder.decode(JobCreateResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func analyzeFromLink(urlString: String) async throws -> JobCreateResponse {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/analyze-from-link")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")
        request.httpBody = try encoder.encode(AnalyzeFromLinkBody(url: urlString))
        let (data, response) = try await session.data(for: request)
        try Self.throwIfNeeded(response, data: data)
        do {
            return try decoder.decode(JobCreateResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func getJob(jobId: String) async throws -> JobResponse {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/\(jobId)")
        var request = URLRequest(url: url)
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")
        let (data, response) = try await session.data(for: request)
        try Self.throwIfNeeded(response, data: data)
        do {
            return try decoder.decode(JobResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func pollJob(
        jobId: String,
        timeoutSeconds: TimeInterval = 120,
        terminal: Set<JobStatus> = [.completed, .failed, .draftReady]
    ) async throws -> JobResponse {
        let deadline = Date().addingTimeInterval(timeoutSeconds)
        while Date() < deadline {
            let job = try await getJob(jobId: jobId)
            if terminal.contains(job.status) {
                return job
            }
            try await Task.sleep(nanoseconds: 800_000_000)
        }
        throw APIError.http(408, "İşlem zaman aşımı")
    }

    func updateBlueprint(jobId: String, blueprint: Blueprint) async throws -> JobResponse {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/\(jobId)/blueprint")
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")
        request.httpBody = try encoder.encode(BlueprintUpdateBody(blueprint: blueprint))
        let (data, response) = try await session.data(for: request)
        try Self.throwIfNeeded(response, data: data)
        do {
            return try decoder.decode(JobResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func uploadUserClip(jobId: String, fileURL: URL) async throws -> JobResponse {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/\(jobId)/user-clip")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let filename = fileURL.lastPathComponent
        let fileData = try Data(contentsOf: fileURL)
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n"
                .data(using: .utf8)!
        )
        body.append("Content-Type: video/mp4\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        try Self.throwIfNeeded(response, data: data)
        do {
            return try decoder.decode(JobResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func startRemake(jobId: String) async throws -> JobResponse {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/\(jobId)/remake")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")
        let (data, response) = try await session.data(for: request)
        try Self.throwIfNeeded(response, data: data)
        do {
            return try decoder.decode(JobResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func downloadDraft(jobId: String) async throws -> URL {
        let url = Self.baseURL.appendingPathComponent("v1/jobs/\(jobId)/draft")
        var request = URLRequest(url: url)
        request.setValue(userId, forHTTPHeaderField: "X-User-Id")
        let (tempURL, response) = try await session.download(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let body = (try? String(contentsOf: tempURL, encoding: .utf8)) ?? ""
            let code = (response as? HTTPURLResponse)?.statusCode ?? 500
            throw APIError.http(code, body)
        }
        let dest = FileManager.default.temporaryDirectory
            .appendingPathComponent("videoart-draft-\(jobId.prefix(8)).mp4")
        try? FileManager.default.removeItem(at: dest)
        try FileManager.default.moveItem(at: tempURL, to: dest)
        return dest
    }

    private static func throwIfNeeded(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.http(http.statusCode, body)
        }
    }
}
