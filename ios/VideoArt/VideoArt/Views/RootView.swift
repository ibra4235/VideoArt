import SwiftUI

struct RootView: View {
    @EnvironmentObject private var flow: AppFlowModel

    var body: some View {
        Group {
            switch flow.step {
            case .welcome:
                WelcomeView()
            case .upload:
                UploadView()
            case .analyzing:
                AnalyzingView()
            case .review:
                BlueprintReviewView()
            }
        }
        .animation(.easeInOut(duration: 0.25), value: flow.step)
    }
}
