import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

struct UploadView: View {
    @EnvironmentObject private var flow: AppFlowModel
    @State private var pickerItem: PhotosPickerItem?
    @State private var showImporter = false

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 20) {
                Text("Referans video")
                    .font(.system(size: 28, weight: .bold, design: .rounded))

                Text("Viral videoyu Photos veya Files’dan seç. Trend feed / link scrape yok — sadece senin dosyan.")
                    .font(.system(size: 15, weight: .regular, design: .rounded))
                    .foregroundStyle(.secondary)

                PhotosPicker(
                    selection: $pickerItem,
                    matching: .videos,
                    photoLibrary: .shared()
                ) {
                    labelRow(title: "Photos’tan seç", subtitle: "Kayıtlı kısa video")
                }
                .onChange(of: pickerItem) { _, item in
                    guard let item else { return }
                    Task { await loadPickerItem(item) }
                }

                Button {
                    showImporter = true
                } label: {
                    labelRow(title: "Files’dan seç", subtitle: "mp4 / mov")
                }
                .buttonStyle(.plain)

                if let error = flow.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .padding(.top, 4)
                }

                Spacer()

                Text("API: \(APIClient.baseURL.absoluteString)")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            .padding(24)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Geri") { flow.reset() }
                }
            }
            .fileImporter(
                isPresented: $showImporter,
                allowedContentTypes: [.movie, .mpeg4Movie, .quickTimeMovie],
                allowsMultipleSelection: false
            ) { result in
                switch result {
                case .success(let urls):
                    guard let url = urls.first else { return }
                    Task { await flow.analyze(fileURL: url) }
                case .failure(let error):
                    flow.errorMessage = error.localizedDescription
                }
            }
        }
    }

    private func labelRow(title: String, subtitle: String) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 17, weight: .semibold, design: .rounded))
                    .foregroundStyle(.primary)
                Text(subtitle)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundStyle(.tertiary)
        }
        .padding(16)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private func loadPickerItem(_ item: PhotosPickerItem) async {
        do {
            guard let movie = try await item.loadTransferable(type: VideoFileTransfer.self) else {
                flow.errorMessage = "Video alınamadı"
                return
            }
            await flow.analyze(fileURL: movie.url)
        } catch {
            flow.errorMessage = error.localizedDescription
        }
    }
}

/// Temporary file copy for PhotosPicker transferable video.
struct VideoFileTransfer: Transferable {
    let url: URL

    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(contentType: .movie) { video in
            SentTransferredFile(video.url)
        } importing: { received in
            let temp = FileManager.default.temporaryDirectory
                .appendingPathComponent("va-ref-\(UUID().uuidString).\(received.file.pathExtension)")
            try? FileManager.default.removeItem(at: temp)
            try FileManager.default.copyItem(at: received.file, to: temp)
            return Self(url: temp)
        }
    }
}
