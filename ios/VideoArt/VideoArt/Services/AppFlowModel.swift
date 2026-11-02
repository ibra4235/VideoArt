import Foundation
import SwiftUI

@MainActor
final class AppFlowModel: ObservableObject {
    enum Step: Equatable {
        case welcome
        case reference
        case analyzing
        case review
        case shootGuidance
        case capture
        case remaking
        case preview
    }

    @Published var step: Step = .welcome
    @Published var isBusy = false
    @Published var statusMessage: String = ""
    @Published var errorMessage: String?
    @Published var jobId: String?
    @Published var blueprint: Blueprint?
    @Published var analyzerName: String = ""
    @Published var sourceFilename: String = ""
    @Published var ingestNote: String?
    @Published var sourceKind: String = "file"
    @Published var localUserClipURL: URL?
    @Published var draftLocalURL: URL?
    @Published var remakeNote: String?

    let api = APIClient()

    init() {
        Analytics.shared.userId = api.userId
        Analytics.shared.baseURL = APIClient.baseURL
    }

    func onAppOpen() {
        Analytics.shared.track(.appOpen, metadata: ["platform": "ios"])
    }

    func goReference() {
        errorMessage = nil
        step = .reference
    }

    func reset() {
        step = .welcome
        isBusy = false
        statusMessage = ""
        errorMessage = nil
        jobId = nil
        blueprint = nil
        analyzerName = ""
        sourceFilename = ""
        ingestNote = nil
        sourceKind = "file"
        localUserClipURL = nil
        draftLocalURL = nil
        remakeNote = nil
    }

    func analyze(fileURL: URL) async {
        errorMessage = nil
        isBusy = true
        step = .analyzing
        statusMessage = "Video yükleniyor…"
        sourceFilename = fileURL.lastPathComponent
        sourceKind = "file"
        ingestNote = nil

        Analytics.shared.track(
            .fileUpload,
            metadata: ["filename": fileURL.lastPathComponent]
        )

        let accessed = fileURL.startAccessingSecurityScopedResource()
        defer {
            if accessed { fileURL.stopAccessingSecurityScopedResource() }
        }

        do {
            let created = try await api.uploadAnalyze(fileURL: fileURL)
            jobId = created.jobId
            Analytics.shared.track(.analyzeStart, jobId: created.jobId, metadata: ["source_kind": "file"])
            statusMessage = "Analiz ediliyor…"
            let job = try await api.pollJob(jobId: created.jobId, terminal: [.completed, .failed])
            try applyAnalyzeResult(job)
            Analytics.shared.track(
                .analyzeComplete,
                jobId: created.jobId,
                metadata: ["status": job.status.rawValue, "source_kind": "file"]
            )
        } catch {
            errorMessage = error.localizedDescription
            Analytics.shared.track(
                .error,
                jobId: jobId,
                metadata: ["stage": "analyze_file", "message": error.localizedDescription]
            )
            step = .reference
        }
        isBusy = false
    }

    func analyzeLink(_ raw: String) async {
        errorMessage = nil
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            errorMessage = "Link yapıştır"
            return
        }
        isBusy = true
        step = .analyzing
        statusMessage = "Link işleniyor (stub)…"
        sourceFilename = trimmed
        sourceKind = "link_stub"

        Analytics.shared.track(.linkSubmit, metadata: ["url_host_hint": String(trimmed.prefix(64))])

        do {
            let created = try await api.analyzeFromLink(urlString: trimmed)
            jobId = created.jobId
            ingestNote = created.ingestNote
            Analytics.shared.track(
                .analyzeStart,
                jobId: created.jobId,
                metadata: ["source_kind": "link_stub"]
            )
            statusMessage = "Analiz ediliyor…"
            let job = try await api.pollJob(jobId: created.jobId, terminal: [.completed, .failed])
            try applyAnalyzeResult(job)
            Analytics.shared.track(
                .analyzeComplete,
                jobId: created.jobId,
                metadata: ["status": job.status.rawValue, "source_kind": "link_stub"]
            )
        } catch {
            errorMessage = error.localizedDescription
            Analytics.shared.track(
                .error,
                jobId: jobId,
                metadata: ["stage": "analyze_link", "message": error.localizedDescription]
            )
            step = .reference
        }
        isBusy = false
    }

    private func applyAnalyzeResult(_ job: JobResponse) throws {
        if job.status == .failed {
            throw APIError.http(500, job.error ?? "Analiz başarısız")
        }
        guard let bp = job.blueprint else {
            throw APIError.emptyResponse
        }
        blueprint = bp
        analyzerName = job.analyzer
        sourceKind = job.sourceKind ?? sourceKind
        ingestNote = job.ingestNote ?? ingestNote
        sourceFilename = job.filename
        statusMessage = "Hazır"
        step = .review
    }

    func saveCaptionEdits() async {
        guard let jobId, var blueprint else { return }
        errorMessage = nil
        isBusy = true
        statusMessage = "Kaydediliyor…"
        do {
            let job = try await api.updateBlueprint(jobId: jobId, blueprint: blueprint)
            self.blueprint = job.blueprint ?? blueprint
            statusMessage = "Blueprint kaydedildi"
        } catch {
            errorMessage = error.localizedDescription
            Analytics.shared.track(
                .error,
                jobId: jobId,
                metadata: ["stage": "blueprint_save", "message": error.localizedDescription]
            )
        }
        isBusy = false
    }

    func updateSceneCaption(sceneId: String, text: String) {
        guard var bp = blueprint else { return }
        guard let idx = bp.scenes.firstIndex(where: { $0.id == sceneId }) else { return }
        bp.scenes[idx].caption.text = text
        blueprint = bp
    }

    func goShootGuidance() {
        errorMessage = nil
        step = .shootGuidance
        Analytics.shared.track(
            .shootGuidanceView,
            jobId: jobId,
            metadata: [
                "duration_sec": blueprint?.shootGuidance.durationSec ?? 0,
            ] as [String: Any]
        )
    }

    func goCapture() {
        errorMessage = nil
        step = .capture
    }

    func trackExportShare() {
        Analytics.shared.track(.exportShare, jobId: jobId, metadata: ["channel": "share_link"])
    }

    func submitUserClip(fileURL: URL) async {
        guard let jobId else {
            errorMessage = "Job yok"
            return
        }
        errorMessage = nil
        isBusy = true
        statusMessage = "Çekim yükleniyor…"

        Analytics.shared.track(
            .clipUpload,
            jobId: jobId,
            metadata: ["filename": fileURL.lastPathComponent]
        )

        let accessed = fileURL.startAccessingSecurityScopedResource()
        defer {
            if accessed { fileURL.stopAccessingSecurityScopedResource() }
        }

        do {
            _ = try await api.uploadUserClip(jobId: jobId, fileURL: fileURL)
            localUserClipURL = fileURL
            statusMessage = "Remake hazırlanıyor…"
            step = .remaking
            Analytics.shared.track(.remakeStart, jobId: jobId)
            _ = try await api.startRemake(jobId: jobId)
            let job = try await api.pollJob(
                jobId: jobId,
                timeoutSeconds: 180,
                terminal: [.draftReady, .failed]
            )
            if job.status == .failed {
                throw APIError.http(500, job.error ?? "Remake başarısız")
            }
            remakeNote = job.remake?.note
            Analytics.shared.track(
                .remakeComplete,
                jobId: jobId,
                metadata: ["duration_ms": job.remake?.durationMs ?? 0] as [String: Any]
            )
            statusMessage = "Draft indiriliyor…"
            draftLocalURL = try await api.downloadDraft(jobId: jobId)
            step = .preview
        } catch {
            errorMessage = error.localizedDescription
            Analytics.shared.track(
                .error,
                jobId: jobId,
                metadata: ["stage": "clip_or_remake", "message": error.localizedDescription]
            )
            step = .capture
        }
        isBusy = false
    }
}
