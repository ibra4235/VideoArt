import Foundation

enum JobStatus: String, Codable, Equatable {
    case queued
    case processing
    case completed
    case failed
    case awaitingClip = "awaiting_clip"
    case remaking
    case draftReady = "draft_ready"
}

struct JobCreateResponse: Codable {
    let jobId: String
    let status: JobStatus
    let ingestNote: String?

    enum CodingKeys: String, CodingKey {
        case status
        case jobId = "job_id"
        case ingestNote = "ingest_note"
    }
}

struct RemakeInfo: Codable, Equatable {
    let draftPath: String?
    let durationMs: Int?
    let genStubScenes: [String]?
    let montage: String?
    let captions: String?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case montage, captions, note
        case draftPath = "draft_path"
        case durationMs = "duration_ms"
        case genStubScenes = "gen_stub_scenes"
    }
}

struct JobResponse: Codable, Equatable {
    let jobId: String
    let status: JobStatus
    let filename: String
    let error: String?
    let blueprint: Blueprint?
    let analyzer: String
    let sourceKind: String?
    let sourceUrl: String?
    let platform: String?
    let ingestNote: String?
    let hasUserClip: Bool?
    let remake: RemakeInfo?
    let draftReady: Bool?

    enum CodingKeys: String, CodingKey {
        case status, filename, error, blueprint, analyzer, platform, remake
        case jobId = "job_id"
        case sourceKind = "source_kind"
        case sourceUrl = "source_url"
        case ingestNote = "ingest_note"
        case hasUserClip = "has_user_clip"
        case draftReady = "draft_ready"
    }
}

struct BlueprintUpdateBody: Encodable {
    let blueprint: Blueprint
}

struct AnalyzeFromLinkBody: Encodable {
    let url: String
}
