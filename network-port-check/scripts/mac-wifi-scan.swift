import Foundation
import CoreWLAN

guard let iface = CWWiFiClient.shared().interface() else { exit(1) }
let nets = try! iface.scanForNetworks(withName: nil)

for n in nets {
    let desc = String(describing: n)
    let sec = desc.components(separatedBy: "security=").last?
        .components(separatedBy: ",").first ?? "?"
    let ssid = n.ssid ?? "(need-location-permission)"
    let ch = n.wlanChannel?.channelNumber ?? 0
    let band = ch > 14 ? "5GHz" : "2.4GHz"

    var w = "-"
    switch n.wlanChannel?.channelWidth.rawValue ?? 0 {
    case 1: w = "20MHz"
    case 2: w = "40MHz"
    case 3: w = "80MHz"
    case 4: w = "160MHz"
    default: break
    }

    print("\(ssid)|\(band)|ch\(ch)|\(w)|\(n.rssiValue)|\(sec)")
}