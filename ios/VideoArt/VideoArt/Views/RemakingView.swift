import SwiftUI

struct RemakingView: View {
    @EnvironmentObject private var flow: AppFlowModel

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            ProgressView()
                .scaleEffect(1.4)
            Text("Remake")
                .font(.system(size: 28, weight: .bold, design: .rounded))
            Text(flow.statusMessage.isEmpty ? "Montaj + caption + gen stub…" : flow.statusMessage)
                .font(.system(size: 16, weight: .medium, design: .rounded))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 28)
            Spacer()
            Text("AI kamera hissi (zoom), sahne kesimleri ve altyazı uygulanıyor.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
                .padding(.bottom, 24)
        }
    }
}
