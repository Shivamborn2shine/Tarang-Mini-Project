package com.tarang.collector.probe

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SentinelNormalizerTest {

    @Test
    fun `normalizeInt converts Int MAX_VALUE sentinel to null and flags unavailable`() {
        val flags = mutableSetOf<String>()
        val result = SentinelNormalizer.normalizeInt(Int.MAX_VALUE, flags)
        assertNull(result)
        assertTrue(flags.contains("unavailable"))
    }

    @Test
    fun `normalizeInt preserves valid negative dBm values`() {
        val flags = mutableSetOf<String>()
        val result = SentinelNormalizer.normalizeInt(-98, flags)
        assertEquals(-98, result)
        assertTrue(flags.isEmpty())
    }

    @Test
    fun `frequencyToWifiTechnology maps 2_4 5 and 6 GHz accurately`() {
        assertEquals("wifi_2_4ghz", SentinelNormalizer.frequencyToWifiTechnology(2437))
        assertEquals("wifi_5ghz", SentinelNormalizer.frequencyToWifiTechnology(5180))
        assertEquals("wifi_6ghz", SentinelNormalizer.frequencyToWifiTechnology(6115))
        assertEquals("wifi_unknown", SentinelNormalizer.frequencyToWifiTechnology(null))
    }

    @Test
    fun `hashBssid is deterministic and case-insensitive`() {
        val a = SentinelNormalizer.hashBssid("AA:BB:CC:DD:EE:FF")
        val b = SentinelNormalizer.hashBssid("aa:bb:cc:dd:ee:ff")
        assertNotNull(a)
        assertEquals(a, b)
        assertEquals(16, a!!.length)
    }
}
