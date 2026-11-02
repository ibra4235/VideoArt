import Foundation
import SwiftUI

@MainActor
final class AppFlowModel: ObservableObject {
    enum Step: Equatable {
        case welcome
        case upload
        case analyzing
        case review
    }

    @Published var step: Step = .welcome
    @Published var isBusy = false
    @Published var statusMessage: String = ""
    @Published var errorMessage: String?
    @Published var jobId: String?
    @Published var blueprint: Blueprint?
    @Published var analyzerName: String = ""
    @Published var sourceFilename: String = ""

    let api = APIClient()

    func goUpload() {
        errorMessage = nil
        step = .upload
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
    }

    func analyze(fileURL: URL) async {
        errorMessage = nil
        isBusy = true
        step = .analyzing
        statusMessage = "Video yükleniyor…"
        sourceFilename = fileURL.lastPathComponent

        // Security-scoped access for Files / Photos exports
        let accessed = fileURL.startAccessingSecurityScopedResource()
        defer {
            if accessed { fileURL.stopAccessingSecurityScopedResource() }
        }

        do {
            let created = try await api.uploadAnalyze(fileURL: fileURL)
            jobId = created.jobId
            statusMessage = "Analiz ediliyor…"
            let job = try await api.pollJob(jobId: created.jobId)
            if job.status == .failed {
                throw APIError.http(500, job.error ?? "Analiz başarısız")
            }
            guard let bp = job.blueprint else {
                throw APIError.emptyResponse
            }
            blueprint = bp
            analyzerName = job.analyzer
            statusMessage = "Hazır"
            step = .review
        } catch {
            errorMessage = error.localizedDescription
            step = .upload
        }
        isBusy = false
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
}
