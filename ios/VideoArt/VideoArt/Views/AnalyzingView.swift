import SwiftUI

struct AnalyzingView: View {
    @EnvironmentObject private var flow: AppFlowModel

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            ProgressView()
                .scaleEffect(1.4)
            Text("Analiz")
                .font(.system(size: 28, weight: .bold, design: .rounded))
            Text(flow.statusMessage)
                .font(.system(size: 16, weight: .medium, design: .rounded))
                .foregroundStyle(.secondary)
            if !flow.sourceFilename.isEmpty {
                Text(flow.sourceFilename)
                    .font(.footnote)
                    .foregroundStyle(.tertiary)
            }
            Spacer()
            Text("Format blueprint çıkarılıyor — kredi yakılmaz.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
                .padding(.bottom, 24)
        }
    }
}
