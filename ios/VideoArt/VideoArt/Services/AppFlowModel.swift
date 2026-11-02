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

        let accessed = fileURL.startAccessingSecurityScopedResource()
        defer {
            if accessed { fileURL.stopAccessingSecurityScopedResource() }
        }

        do {
            let created = try await api.uploadAnalyze(fileURL: fileURL)
            jobId = created.jobId
            statusMessage = "Analiz ediliyor…"
            let job = try await api.pollJob(jobId: created.jobId, terminal: [.completed, .failed])
            try applyAnalyzeResult(job)
        } catch {
            errorMessage = error.localizedDescription
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

        do {
            let created = try await api.analyzeFromLink(urlString: trimmed)
            jobId = created.jobId
            ingestNote = created.ingestNote
            statusMessage = "Analiz ediliyor…"
            let job = try await api.pollJob(jobId: created.jobId, terminal: [.completed, .failed])
            try applyAnalyzeResult(job)
        } catch {
            errorMessage = error.localizedDescription
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
    }

    func goCapture() {
        errorMessage = nil
        step = .capture
    }

    func submitUserClip(fileURL: URL) async {
        guard let jobId else {
            errorMessage = "Job yok"
            return
        }
        errorMessage = nil
        isBusy = true
        statusMessage = "Çekim yükleniyor…"

        let accessed = fileURL.startAccessingSecurityScopedResource()
        defer {
            if accessed { fileURL.stopAccessingSecurityScopedResource() }
        }

        do {
            _ = try await api.uploadUserClip(jobId: jobId, fileURL: fileURL)
            localUserClipURL = fileURL
            statusMessage = "Remake hazırlanıyor…"
            step = .remaking
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
            statusMessage = "Draft indiriliyor…"
            draftLocalURL = try await api.downloadDraft(jobId: jobId)
            step = .preview
        } catch {
            errorMessage = error.localizedDescription
            step = .capture
        }
        isBusy = false
    }
}
