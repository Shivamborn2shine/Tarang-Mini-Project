package com.tarang.collector.probe

import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

/**
 * Normalizes Android sentinel values (e.g., CellInfo.UNAVAILABLE / Int.MAX_VALUE)
 * into nullable values so unavailable telemetry is never misrepresented as a real signal.
 */
object SentinelNormalizer {
    const val ANDROID_UNAVAILABLE: Int = Int.MAX_VALUE

    fun normalizeInt(value: Int, flags: MutableSet<String>): Int? {
        if (value == ANDROID_UNAVAILABLE || value == Int.MIN_VALUE) {
            flags.add("unavailable")
            return null
        }
        return value
    }

    fun frequencyToWifiTechnology(frequencyMhz: Int?): String {
        if (frequencyMhz == null) return "wifi_unknown"
        return when (frequencyMhz) {
            in 2400..2500 -> "wifi_2_4ghz"
            in 4900..5900 -> "wifi_5ghz"
            in 5925..7125 -> "wifi_6ghz"
            else -> "wifi_unknown"
        }
    }

    fun hashBssid(bssid: String?, projectSalt: String = "tarang-local-sprint0"): String? {
        if (bssid.isNullOrBlank()) return null
        val normalized = bssid.trim().lowercase()
        val bytes = MessageDigest.getInstance("SHA-256")
            .digest("$projectSalt:$normalized".toByteArray(Charsets.UTF_8))
        return bytes.take(8).joinToString("") { "%02x".format(it) }
    }
}

data class CapabilityProbeReport(
    val permissionFineLocation: Boolean,
    val permissionReadPhoneState: Boolean,
    val permissionNearbyWifi: Boolean,
    val wifiSupported: Boolean,
    val wifiScanResultCount: Int,
    val cellularInfoCount: Int,
    val cellularTechnologiesObserved: List<String>,
    val sampleObservations: List<JSONObject>,
    val notes: List<String>,
) {
    fun toSanitizedJson(): String {
        val root = JSONObject()
        root.put("permission_fine_location", permissionFineLocation)
        root.put("permission_read_phone_state", permissionReadPhoneState)
        root.put("permission_nearby_wifi", permissionNearbyWifi)
        root.put("wifi_supported", wifiSupported)
        root.put("wifi_scan_result_count", wifiScanResultCount)
        root.put("cellular_info_count", cellularInfoCount)
        root.put("cellular_technologies", JSONArray(cellularTechnologiesObserved))
        root.put("notes", JSONArray(notes))
        root.put("observations", JSONArray(sampleObservations))
        return root.toString(2)
    }
}
