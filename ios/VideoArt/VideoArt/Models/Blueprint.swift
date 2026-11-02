import Foundation

struct Blueprint: Codable, Equatable {
    var version: Int
    var source: SourceInfo
    var globalStyle: GlobalStyle
    var scenes: [Scene]
    var audio: AudioInfo
    var export: ExportInfo
    var shootGuidance: ShootGuidance

    enum CodingKeys: String, CodingKey {
        case version, source, scenes, audio, export
        case globalStyle = "global_style"
        case shootGuidance = "shoot_guidance"
    }

    init(
        version: Int,
        source: SourceInfo,
        globalStyle: GlobalStyle,
        scenes: [Scene],
        audio: AudioInfo,
        export: ExportInfo,
        shootGuidance: ShootGuidance = .default
    ) {
        self.version = version
        self.source = source
        self.globalStyle = globalStyle
        self.scenes = scenes
        self.audio = audio
        self.export = export
        self.shootGuidance = shootGuidance
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        version = try c.decode(Int.self, forKey: .version)
        source = try c.decode(SourceInfo.self, forKey: .source)
        globalStyle = try c.decode(GlobalStyle.self, forKey: .globalStyle)
        scenes = try c.decode([Scene].self, forKey: .scenes)
        audio = try c.decode(AudioInfo.self, forKey: .audio)
        export = try c.decode(ExportInfo.self, forKey: .export)
        shootGuidance = try c.decodeIfPresent(ShootGuidance.self, forKey: .shootGuidance) ?? .default
    }
}

struct ShootGuidance: Codable, Equatable {
    var mode: String
    var title: String
    var instruction: String
    var durationSec: Int
    var tips: [String]

    enum CodingKeys: String, CodingKey {
        case mode, title, instruction, tips
        case durationSec = "duration_sec"
    }

    static let `default` = ShootGuidance(
        mode: "flat_talking_head",
        title: "Tek plan çekim",
        instruction: "Otur, kameraya bak, gülümse, konuş",
        durationSec: 15,
        tips: [
            "Telefonu dikey tut (9:16)",
            "Yüzün çerçevede net görünsün",
            "Arka plan sade olsun",
            "Kendi cümlelerinle konuş — metni ezberleme",
        ]
    )
}

struct SourceInfo: Codable, Equatable {
    var filename: String
    var durationMs: Int
    var aspect: String
    var fpsHint: Double
    var sourceKind: String?
    var sourceUrl: String?
    var platform: String?

    enum CodingKeys: String, CodingKey {
        case filename, aspect
        case durationMs = "duration_ms"
        case fpsHint = "fps_hint"
        case sourceKind = "source_kind"
        case sourceUrl = "source_url"
        case platform
    }
}

struct GlobalStyle: Codable, Equatable {
    var mood: String
    var colorGrade: String
    var transitionDefault: String
    var captionStyle: CaptionStyle
    var cameraNotes: String

    enum CodingKeys: String, CodingKey {
        case mood
        case colorGrade = "color_grade"
        case transitionDefault = "transition_default"
        case captionStyle = "caption_style"
        case cameraNotes = "camera_notes"
    }
}

struct CaptionStyle: Codable, Equatable {
    var placement: String
    var fontHint: String
    var emphasis: String

    enum CodingKeys: String, CodingKey {
        case placement, emphasis
        case fontHint = "font_hint"
    }
}

struct Scene: Codable, Equatable, Identifiable {
    var id: String
    var startMs: Int
    var endMs: Int
    var role: String
    var shot: String
    var action: String
    var caption: SceneCaption
    var genVideo: GenVideo
    var userClip: UserClip

    enum CodingKeys: String, CodingKey {
        case id, role, shot, action, caption
        case startMs = "start_ms"
        case endMs = "end_ms"
        case genVideo = "gen_video"
        case userClip = "user_clip"
    }
}

struct SceneCaption: Codable, Equatable {
    var text: String
    var startMs: Int
    var endMs: Int

    enum CodingKeys: String, CodingKey {
        case text
        case startMs = "start_ms"
        case endMs = "end_ms"
    }
}

struct GenVideo: Codable, Equatable {
    var needed: Bool
    var promptHint: String?

    enum CodingKeys: String, CodingKey {
        case needed
        case promptHint = "prompt_hint"
    }
}

struct UserClip: Codable, Equatable {
    var required: Bool
    var guidance: String
}

struct AudioInfo: Codable, Equatable {
    var policy: String
    var beatHints: [String]
    var ttsOptional: Bool

    enum CodingKeys: String, CodingKey {
        case policy
        case beatHints = "beat_hints"
        case ttsOptional = "tts_optional"
    }
}

struct ExportInfo: Codable, Equatable {
    var targets: [String]
    var maxDurationMs: Int

    enum CodingKeys: String, CodingKey {
        case targets
        case maxDurationMs = "max_duration_ms"
    }
}
