// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FlipperStateMenu",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "flipper-state-menu", targets: ["FlipperStateMenu"])],
    targets: [.executableTarget(name: "FlipperStateMenu")]
)
