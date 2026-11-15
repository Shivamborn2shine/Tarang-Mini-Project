package com.tarang.collector

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.tarang.collector.probe.CapabilityProbeReport
import com.tarang.collector.probe.RadioCapabilityProbe

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Scaffold { innerPadding ->
                    CapabilityProbeScreen(modifier = Modifier.padding(innerPadding))
                }
            }
        }
    }
}

@Composable
fun CapabilityProbeScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val probe = remember(context) { RadioCapabilityProbe(context) }
    var report by remember { mutableStateOf<CapabilityProbeReport?>(probe.runProbe()) }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) {
        report = probe.runProbe()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "TARANG — Sprint 0 Radio Probe",
            style = MaterialTheme.typography.headlineSmall,
        )
        Text(
            text = "Honest device capability check for Wi-Fi and LTE/5G NR telemetry.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { permissionLauncher.launch(probe.requiredPermissions()) }) {
                Text("Request Permissions")
            }
            OutlinedButton(onClick = { report = probe.runProbe() }) {
                Text("Run Probe")
            }
        }

        report?.let { r ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Permissions", style = MaterialTheme.typography.titleMedium)
                    Text("Fine Location: ${r.permissionFineLocation}")
                    Text("Phone State: ${r.permissionReadPhoneState}")
                    Text("Nearby Wi-Fi: ${r.permissionNearbyWifi}")
                    Spacer(modifier = Modifier.height(6.dp))
                    Text("Observed Sensors", style = MaterialTheme.typography.titleMedium)
                    Text("Wi-Fi Scan Results: ${r.wifiScanResultCount}")
                    Text("Cellular CellInfo Entries: ${r.cellularInfoCount}")
                    Text("Cellular Techs: ${r.cellularTechnologiesObserved.ifEmpty { listOf("None / Denied") }.joinToString()}")
                    if (r.notes.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Text("Notes: ${r.notes.joinToString(" | ")}")
                    }
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Sanitized Canonical Payload Preview", style = MaterialTheme.typography.titleMedium)
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = r.toSanitizedJson(),
                        fontFamily = FontFamily.Monospace,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
