package com.tarang.collector.probe

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import android.os.Build
import android.os.SystemClock
import android.telephony.CellInfo
import android.telephony.CellInfoGsm
import android.telephony.CellInfoLte
import android.telephony.CellInfoNr
import android.telephony.CellInfoWcdma
import android.telephony.CellSignalStrengthLte
import android.telephony.CellSignalStrengthNr
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.UUID

/**
 * Sprint 0 Android radio capability probe.
 * Reads Wi-Fi and Cellular APIs safely without fabricating missing metrics.
 */
class RadioCapabilityProbe(private val context: Context) {

    fun requiredPermissions(): Array<String> {
        val perms = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.READ_PHONE_STATE,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.NEARBY_WIFI_DEVICES)
        }
        return perms.toTypedArray()
    }

    private fun hasPermission(permission: String): Boolean =
        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    fun runProbe(
        sessionId: String = UUID.randomUUID().toString(),
        deviceId: String = UUID.randomUUID().toString(),
        sanitize: Boolean = true,
    ): CapabilityProbeReport {
        val fineLoc = hasPermission(Manifest.permission.ACCESS_FINE_LOCATION)
        val phoneState = hasPermission(Manifest.permission.READ_PHONE_STATE)
        val nearbyWifi = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            hasPermission(Manifest.permission.NEARBY_WIFI_DEVICES)
        } else {
            true
        }

        val notes = mutableListOf<String>()
        val observations = mutableListOf<JSONObject>()
        val nowInstant = Instant.now()
        val elapsedMs = SystemClock.elapsedRealtime()

        val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        var wifiScanCount = 0
        if (wifiManager == null) {
            notes.add("WifiManager unavailable on this device.")
        } else if (!fineLoc && !nearbyWifi) {
            notes.add("Wi-Fi scan results unavailable: location/nearby-wifi permission denied.")
        } else {
            val scanResults = wifiManager.scanResults ?: emptyList()
            wifiScanCount = scanResults.size
            scanResults.take(3).forEach { scan ->
                val scanAgeMs = (elapsedMs - (scan.timestamp / 1000L)).coerceAtLeast(0L)
                val observedAt = nowInstant.minusMillis(scanAgeMs)
                val flags = mutableSetOf<String>()
                if (scanAgeMs > 30_000L) flags.add("stale_scan")
                if (sanitize) flags.add("sanitized")

                @Suppress("DEPRECATION")
                val rawSsid = scan.SSID
                val ssidVal = if (sanitize && !rawSsid.isNullOrBlank()) "<REDACTED>" else rawSsid

                observations.add(
                    JSONObject().apply {
                        put("schema_version", 1)
                        put("id", UUID.randomUUID().toString())
                        put("session_id", sessionId)
                        put("device_id", deviceId)
                        put("kind", "wifi")
                        put("technology", SentinelNormalizer.frequencyToWifiTechnology(scan.frequency))
                        put("source", "android_wifi")
                        put("observed_at", observedAt.toString())
                        put("recorded_at", nowInstant.toString())
                        put("freshness_ms", scanAgeMs)
                        put("location", JSONObject().put("kind", "unknown"))
                        put(
                            "metrics",
                            JSONObject().apply {
                                put("rssi_dbm", scan.level)
                                put("frequency_mhz", scan.frequency)
                                put("quality_percent", JSONObject.NULL)
                            }
                        )
                        put(
                            "network",
                            JSONObject().apply {
                                put("ssid", ssidVal ?: JSONObject.NULL)
                                put("bssid_hash", SentinelNormalizer.hashBssid(scan.BSSID) ?: JSONObject.NULL)
                                put("is_connected", false)
                            }
                        )
                        put("flags", JSONArray(flags.toList()))
                    }
                )
            }
        }

        val telephony = context.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager
        val cellTechs = mutableSetOf<String>()
        var cellCount = 0
        if (telephony == null) {
            notes.add("TelephonyManager unavailable on this device.")
        } else if (!fineLoc) {
            notes.add("Cellular CellInfo unavailable: ACCESS_FINE_LOCATION denied.")
        } else {
            val cellInfos: List<CellInfo> = telephony.allCellInfo ?: emptyList()
            cellCount = cellInfos.size
            cellInfos.take(3).forEach { cell ->
                val obs = mapCellInfo(cell, sessionId, deviceId, nowInstant, elapsedMs, telephony.networkOperatorName, sanitize)
                if (obs != null) {
                    cellTechs.add(obs.getString("technology"))
                    observations.add(obs)
                }
            }
        }

        return CapabilityProbeReport(
            permissionFineLocation = fineLoc,
            permissionReadPhoneState = phoneState,
            permissionNearbyWifi = nearbyWifi,
            wifiSupported = wifiManager != null,
            wifiScanResultCount = wifiScanCount,
            cellularInfoCount = cellCount,
            cellularTechnologiesObserved = cellTechs.toList(),
            sampleObservations = observations,
            notes = notes,
        )
    }

    private fun mapCellInfo(
        cell: CellInfo,
        sessionId: String,
        deviceId: String,
        nowInstant: Instant,
        elapsedMs: Long,
        operatorName: String?,
        sanitize: Boolean,
    ): JSONObject? {
        val flags = mutableSetOf<String>()
        if (sanitize) flags.add("sanitized")

        val ageMs = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            (elapsedMs - cell.timestampMillis).coerceAtLeast(0L)
        } else {
            @Suppress("DEPRECATION")
            (elapsedMs - (cell.timeStamp / 1_000_000L)).coerceAtLeast(0L)
        }
        val observedAt = nowInstant.minusMillis(ageMs)

        val metrics = JSONObject()
        val technology: String
        when (cell) {
            is CellInfoLte -> {
                technology = "lte"
                val sig: CellSignalStrengthLte = cell.cellSignalStrength
                metrics.put("rsrp_dbm", SentinelNormalizer.normalizeInt(sig.rsrp, flags) ?: JSONObject.NULL)
                metrics.put("rsrq_db", SentinelNormalizer.normalizeInt(sig.rsrq, flags) ?: JSONObject.NULL)
                metrics.put("sinr_db", SentinelNormalizer.normalizeInt(sig.rssnr, flags) ?: JSONObject.NULL)
                metrics.put("is_registered", cell.isRegistered)
            }
            is CellInfoNr -> {
                technology = "nr"
                val sig = cell.cellSignalStrength as? CellSignalStrengthNr
                if (sig != null) {
                    metrics.put("rsrp_dbm", SentinelNormalizer.normalizeInt(sig.ssRsrp, flags) ?: JSONObject.NULL)
                    metrics.put("rsrq_db", SentinelNormalizer.normalizeInt(sig.ssRsrq, flags) ?: JSONObject.NULL)
                    metrics.put("sinr_db", SentinelNormalizer.normalizeInt(sig.ssSinr, flags) ?: JSONObject.NULL)
                } else {
                    flags.add("unsupported")
                }
                metrics.put("is_registered", cell.isRegistered)
            }
            is CellInfoWcdma -> {
                technology = "wcdma"
                metrics.put("rssi_dbm", SentinelNormalizer.normalizeInt(cell.cellSignalStrength.dbm, flags) ?: JSONObject.NULL)
                metrics.put("is_registered", cell.isRegistered)
            }
            is CellInfoGsm -> {
                technology = "gsm"
                metrics.put("rssi_dbm", SentinelNormalizer.normalizeInt(cell.cellSignalStrength.dbm, flags) ?: JSONObject.NULL)
                metrics.put("is_registered", cell.isRegistered)
            }
            else -> {
                technology = "unknown"
                flags.add("unsupported")
            }
        }

        return JSONObject().apply {
            put("schema_version", 1)
            put("id", UUID.randomUUID().toString())
            put("session_id", sessionId)
            put("device_id", deviceId)
            put("kind", "cellular")
            put("technology", technology)
            put("source", "android_telephony")
            put("observed_at", observedAt.toString())
            put("recorded_at", nowInstant.toString())
            put("freshness_ms", ageMs)
            put("location", JSONObject().put("kind", "unknown"))
            put("metrics", metrics)
            put(
                "network",
                JSONObject().apply {
                    put("operator_name", operatorName?.takeIf { it.isNotBlank() } ?: JSONObject.NULL)
                }
            )
            put("flags", JSONArray(flags.toList()))
        }
    }
}
