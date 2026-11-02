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
                        }

                        Section("Stil") {
                            LabeledContent("Mood", value: blueprint.globalStyle.mood)
                            LabeledContent("Renk", value: blueprint.globalStyle.colorGrade)
                            Text(blueprint.globalStyle.cameraNotes)
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
                                    Text("Gen video: gerektiğinde (bu dilimde stub)")
                                        .font(.caption2)
                                        .foregroundStyle(.orange)
                                }
                                Text("Çekim: \(scene.userClip.guidance)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
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
            .overlay(alignment: .bottom) {
                if let error = flow.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.white)
                        .padding(12)
                        .background(.red.opacity(0.9))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                        .padding()
                } else if savedToast {
                    Text(flow.statusMessage)
                        .font(.footnote)
                        .foregroundStyle(.white)
                        .padding(12)
                        .background(.green.opacity(0.9))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                        .padding()
                        .onAppear {
                            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                savedToast = false
                            }
                        }
                }
            }
        }
    }

    private func formatMs(_ ms: Int) -> String {
        let s = Double(ms) / 1000.0
        return String(format: "%.1fs", s)
    }
}
