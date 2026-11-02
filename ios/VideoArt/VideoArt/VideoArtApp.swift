import SwiftUI

@main
struct VideoArtApp: App {
    @StateObject private var flow = AppFlowModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(flow)
        }
    }
}
