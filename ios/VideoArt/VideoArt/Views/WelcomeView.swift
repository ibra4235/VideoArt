import SwiftUI

struct WelcomeView: View {
    @EnvironmentObject private var flow: AppFlowModel

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.06, green: 0.09, blue: 0.14),
                    Color(red: 0.12, green: 0.18, blue: 0.22),
                    Color(red: 0.08, green: 0.22, blue: 0.20),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 28) {
                Spacer()

                Text("VideoArt")
                    .font(.system(size: 48, weight: .bold, design: .rounded))
                    .foregroundStyle(.white)

                Text("Format ilhamı / kendi içeriğin")
                    .font(.system(size: 20, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color(red: 0.55, green: 0.92, blue: 0.78))

                Text("Instagram veya TikTok linkini yapıştır. VideoArt formatı çözer; sen tek düz talking-head çekim yaparsın — kesme, kamera hissi ve caption’ı remake uygular.")
                    .font(.system(size: 16, weight: .regular, design: .rounded))
                    .foregroundStyle(.white.opacity(0.78))
                    .fixedSize(horizontal: false, vertical: true)

                Button {
                    flow.goReference()
                } label: {
                    Text("Başla")
                        .font(.system(size: 17, weight: .semibold, design: .rounded))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color(red: 0.20, green: 0.85, blue: 0.62))
                        .foregroundStyle(Color(red: 0.05, green: 0.12, blue: 0.10))
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
                .padding(.top, 8)

                Text("Sign in with Apple / StoreKit bu dilimde yok. Link indirme stub (ToS).")
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.45))

                Spacer()
            }
            .padding(.horizontal, 28)
        }
    }
}
