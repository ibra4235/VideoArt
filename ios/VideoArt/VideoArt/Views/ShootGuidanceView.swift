import SwiftUI

struct ShootGuidanceView: View {
    @EnvironmentObject private var flow: AppFlowModel

    private var guidance: ShootGuidance {
        flow.blueprint?.shootGuidance ?? .default
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 24) {
                Text(guidance.title)
                    .font(.system(size: 28, weight: .bold, design: .rounded))

                Text(guidance.instruction)
                    .font(.system(size: 22, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color(red: 0.12, green: 0.45, blue: 0.36))
                    .fixedSize(horizontal: false, vertical: true)

                Text("~\(guidance.durationSec) saniye · düz talking-head · tek çekim")
                    .font(.system(size: 15, weight: .medium, design: .rounded))
                    .foregroundStyle(.secondary)

                VStack(alignment: .leading, spacing: 12) {
                    ForEach(guidance.tips, id: \.self) { tip in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(Color(red: 0.20, green: 0.85, blue: 0.62))
                            Text(tip)
                                .font(.system(size: 15, weight: .regular, design: .rounded))
                        }
                    }
                }
                .padding(.top, 4)

                Text("Kesme, hafif zoom ve caption’ları remake uygular — sen sadece düz konuş.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding(.top, 8)

                Spacer()

                Button {
                    flow.goCapture()
                } label: {
                    Text("Kamerayı aç / klip seç")
                        .font(.system(size: 17, weight: .semibold, design: .rounded))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color(red: 0.20, green: 0.85, blue: 0.62))
                        .foregroundStyle(Color(red: 0.05, green: 0.12, blue: 0.10))
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
            }
            .padding(24)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Blueprint") { flow.step = .review }
                }
            }
        }
    }
}
