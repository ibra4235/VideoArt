import SwiftUI

struct BlueprintReviewView: View {
    @EnvironmentObject private var flow: AppFlowModel
    @State private var savedToast = false

    var body: some View {
        NavigationStack {
            Group {
                if let blueprint = flow.blueprint {
                    List {
                        Section("Kaynak") {
                            LabeledContent("Dosya", value: blueprint.source.filename)
                            LabeledContent("Süre", value: formatMs(blueprint.source.durationMs))
                            LabeledContent("En-boy", value: blueprint.source.aspect)
                            LabeledContent("Analiz", value: flow.analyzerName.isEmpty ? "—" : flow.analyzerName)
                            if let kind = blueprint.source.sourceKind ?? Optional(flow.sourceKind) {
                                LabeledContent("Giriş", value: kind)
                            }
                            if let platform = blueprint.source.platform {
                                LabeledContent("Platform", value: platform)
                            }
                        }

                        if let note = flow.ingestNote, !note.isEmpty {
                            Section("Link stub notu") {
                                Text(note)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Section("Stil") {
                            LabeledContent("Mood", value: blueprint.globalStyle.mood)
                            LabeledContent("Renk", value: blueprint.globalStyle.colorGrade)
                            Text(blueprint.globalStyle.cameraNotes)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }

                        Section("Çekim özeti") {
                            Text(blueprint.shootGuidance.instruction)
                                .font(.system(size: 16, weight: .semibold, design: .rounded))
                            Text("~\(blueprint.shootGuidance.durationSec) sn · tek talking-head")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }

                        Section {
                            Text("Caption metinleri ilham metnidir — bire bir kopya değil. Düzenleyebilirsin.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                                .listRowBackground(Color.clear)
                        }

                        ForEach(blueprint.scenes) { scene in
                            Section("\(scene.id.uppercased()) · \(scene.role)") {
                                LabeledContent("Zaman", value: "\(formatMs(scene.startMs)) – \(formatMs(scene.endMs))")
                                LabeledContent("Shot", value: scene.shot)
                                Text(scene.action)
                                    .font(.footnote)
                                TextField(
                                    "İlham caption",
                                    text: Binding(
                                        get: { scene.caption.text },
                                        set: { flow.updateSceneCaption(sceneId: scene.id, text: $0) }
                                    ),
                                    axis: .vertical
                                )
                                .lineLimit(2...4)
                                if scene.genVideo.needed {
                                    Text("Gen video: remake’te stub placeholder")
                                        .font(.caption2)
                                        .foregroundStyle(.orange)
                                }
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                } else {
                    ContentUnavailableView("Blueprint yok", systemImage: "film")
                }
            }
            .navigationTitle("Blueprint")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Başa dön") { flow.reset() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            await flow.saveCaptionEdits()
                            savedToast = flow.errorMessage == nil
                        }
                    } label: {
                        if flow.isBusy {
                            ProgressView()
                        } else {
                            Text("Kaydet")
                        }
                    }
                    .disabled(flow.isBusy || flow.blueprint == nil)
                }
            }
            .safeAreaInset(edge: .bottom) {
                VStack(spacing: 8) {
                    if let error = flow.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(.white)
                            .padding(10)
                            .frame(maxWidth: .infinity)
                            .background(.red.opacity(0.9))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                    } else if savedToast {
                        Text(flow.statusMessage)
                            .font(.footnote)
                            .foregroundStyle(.white)
                            .padding(10)
                            .frame(maxWidth: .infinity)
                            .background(.green.opacity(0.9))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                            .onAppear {
                                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                    savedToast = false
                                }
                            }
                    }
                    Button {
                        Task {
                            await flow.saveCaptionEdits()
                            flow.goShootGuidance()
                        }
                    } label: {
                        Text("Çekim rehberine geç")
                            .font(.system(size: 17, weight: .semibold, design: .rounded))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(Color(red: 0.20, green: 0.85, blue: 0.62))
                            .foregroundStyle(Color(red: 0.05, green: 0.12, blue: 0.10))
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .disabled(flow.blueprint == nil)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(.ultraThinMaterial)
            }
        }
    }

    private func formatMs(_ ms: Int) -> String {
        let s = Double(ms) / 1000.0
        return String(format: "%.1fs", s)
    }
}
