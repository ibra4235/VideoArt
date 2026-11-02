import AVKit
import SwiftUI

struct PreviewExportView: View {
    @EnvironmentObject private var flow: AppFlowModel
    @State private var shareURL: URL?

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("Önizleme")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .frame(maxWidth: .infinity, alignment: .leading)

                if let url = flow.draftLocalURL {
                    VideoPlayer(player: AVPlayer(url: url))
                        .frame(maxWidth: .infinity)
                        .aspectRatio(9 / 16, contentMode: .fit)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .background(Color.black.opacity(0.08))
                } else {
                    ContentUnavailableView("Draft yok", systemImage: "film")
                }

                if let note = flow.remakeNote, !note.isEmpty {
                    Text(note)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                if let error = flow.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                Spacer(minLength: 0)

                if let url = flow.draftLocalURL {
                    ShareLink(item: url) {
                        Text("Paylaş / Kaydet")
                            .font(.system(size: 17, weight: .semibold, design: .rounded))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(Color(red: 0.20, green: 0.85, blue: 0.62))
                            .foregroundStyle(Color(red: 0.05, green: 0.12, blue: 0.10))
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                }

                Button("Yeni remake") {
                    flow.reset()
                }
                .font(.system(size: 15, weight: .medium, design: .rounded))
                .padding(.bottom, 8)
            }
            .padding(24)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Başa dön") { flow.reset() }
                }
            }
        }
    }
}
