import Foundation

enum JobStatus: String, Codable, Equatable {
    case queued
    case processing
    case completed
    case failed
}

struct JobCreateResponse: Codable {
    let jobId: String
    let status: JobStatus

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case status
    }
}

struct JobResponse: Codable, Equatable {
    let jobId: String
    let status: JobStatus
    let filename: String
    let error: String?
    let blueprint: Blueprint?
    let analyzer: String

    enum CodingKeys: String, CodingKey {
        case status, filename, error, blueprint, analyzer
        case jobId = "job_id"
    }
}

struct BlueprintUpdateBody: Encodable {
    let blueprint: Blueprint
}
