import PhotosUI
import SwiftUI
import UniformTypeIdentifiers
import UIKit

struct CaptureView: View {
    @EnvironmentObject private var flow: AppFlowModel
    @State private var pickerItem: PhotosPickerItem?
    @State private var showImporter = false
    @State private var showCamera = false

    private var seconds: Int {
        flow.blueprint?.shootGuidance.durationSec ?? 15
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 18) {
                Text("Kendi çekimin")
                    .font(.system(size: 28, weight: .bold, design: .rounded))

                Text("Tek düz talking-head klip kaydet veya yükle (~\(seconds) sn).")
                    .font(.system(size: 15, weight: .regular, design: .rounded))
                    .foregroundStyle(.secondary)

                Button {
                    if UIImagePickerController.isSourceTypeAvailable(.camera) {
                        showCamera = true
                    } else {
                        flow.errorMessage = "Simülatörde kamera yok — Photos veya Files kullan."
                    }
                } label: {
                    labelRow(title: "Kameradan çek", subtitle: "Ön kamera · dikey")
                }
                .buttonStyle(.plain)

                PhotosPicker(
                    selection: $pickerItem,
                    matching: .videos,
                    photoLibrary: .shared()
                ) {
                    labelRow(title: "Photos’tan seç", subtitle: "Önceden çekilmiş klip")
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
                }

                Spacer()
            }
            .padding(24)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Rehber") { flow.goShootGuidance() }
                }
            }
            .sheet(isPresented: $showCamera) {
                CameraPicker { url in
                    showCamera = false
                    guard let url else { return }
                    Task { await flow.submitUserClip(fileURL: url) }
                }
                .ignoresSafeArea()
            }
            .fileImporter(
                isPresented: $showImporter,
                allowedContentTypes: [.movie, .mpeg4Movie, .quickTimeMovie],
                allowsMultipleSelection: false
            ) { result in
                switch result {
                case .success(let urls):
                    guard let url = urls.first else { return }
                    Task { await flow.submitUserClip(fileURL: url) }
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
            await flow.submitUserClip(fileURL: movie.url)
        } catch {
            flow.errorMessage = error.localizedDescription
        }
    }
}

struct CameraPicker: UIViewControllerRepresentable {
    var onFinish: (URL?) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.mediaTypes = ["public.movie"]
        picker.cameraDevice = .front
        picker.videoQuality = .typeHigh
        picker.delegate = context.coordinator
        picker.modalPresentationStyle = .fullScreen
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onFinish: onFinish)
    }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onFinish: (URL?) -> Void

        init(onFinish: @escaping (URL?) -> Void) {
            self.onFinish = onFinish
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            onFinish(nil)
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            if let url = info[.mediaURL] as? URL {
                let dest = FileManager.default.temporaryDirectory
                    .appendingPathComponent("va-capture-\(UUID().uuidString).\(url.pathExtension)")
                try? FileManager.default.removeItem(at: dest)
                try? FileManager.default.copyItem(at: url, to: dest)
                onFinish(dest)
            } else {
                onFinish(nil)
            }
        }
    }
}
