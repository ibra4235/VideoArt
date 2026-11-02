import SwiftUI

struct RootView: View {
    @EnvironmentObject private var flow: AppFlowModel

    var body: some View {
        Group {
            switch flow.step {
            case .welcome:
                WelcomeView()
            case .reference:
                ReferenceInputView()
            case .analyzing:
                AnalyzingView()
            case .review:
                BlueprintReviewView()
            case .shootGuidance:
                ShootGuidanceView()
            case .capture:
                CaptureView()
            case .remaking:
                RemakingView()
            case .preview:
                PreviewExportView()
            }
        }
        .animation(.easeInOut(duration: 0.25), value: flow.step)
    }
}
