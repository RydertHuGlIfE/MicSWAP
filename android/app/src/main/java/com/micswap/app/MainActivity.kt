
package com.micswap.app

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.io.BufferedOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : Activity() {

    private var audioRecord: AudioRecord? = null
    private var recordingThread: Thread? = null
    private val running = AtomicBoolean(false)

    private lateinit var status: TextView
    private lateinit var toggleButton: Button

    private val sampleRate = 48000
    private val port = 50005

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        status = TextView(this).apply {
            text = "Mic Transfer OFF"
            textSize = 22f
            gravity = Gravity.CENTER
        }

        toggleButton = Button(this).apply {
            text = "Mic Transfer ON"
            setOnClickListener {
                if (running.get()) stopMic() else requestMicPermission()
            }
        }

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(32, 32, 32, 32)
            addView(status)
            addView(toggleButton)
        }

        setContentView(layout)
    }

    private fun requestMicPermission() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startMic()
        } else {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 100)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode == 100 &&
            grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
        ) {
            startMic()
        } else {
            status.text = "Microphone permission denied"
        }
    }

    private fun startMic() {
        val minBuffer = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        if (minBuffer <= 0) {
            status.text = "Audio configuration unsupported"
            return
        }

        val recorder = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            minBuffer * 2
        )

        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            recorder.release()
            status.text = "Microphone initialization failed"
            return
        }

        audioRecord = recorder
        running.set(true)
        toggleButton.isEnabled = false
        status.text = "Connecting to PC..."

        recordingThread = Thread {
            var socket: Socket? = null
            var output: BufferedOutputStream? = null

            try {
                socket = Socket()
                socket.connect(InetSocketAddress("127.0.0.1", port), 5000)
                output = BufferedOutputStream(socket.getOutputStream())

                recorder.startRecording()

                runOnUiThread {
                    status.text = "USB audio transfer ACTIVE"
                    toggleButton.text = "Mic Transfer OFF"
                    toggleButton.isEnabled = true
                }

                val samples = ShortArray(minBuffer / 2)
                val bytes = ByteArray(samples.size * 2)

                while (running.get()) {
                    val count = recorder.read(
                        samples, 0, samples.size, AudioRecord.READ_BLOCKING
                    )

                    if (count < 0) {
                        throw RuntimeException("AudioRecord read failed: $count")
                    }

                    if (count == 0) continue

                    // Convert signed 16-bit samples to little-endian PCM.
                    for (i in 0 until count) {
                        val sample = samples[i].toInt()
                        bytes[i * 2] = (sample and 0xff).toByte()
                        bytes[i * 2 + 1] =
                            ((sample shr 8) and 0xff).toByte()
                    }

                    output.write(bytes, 0, count * 2)
                    output.flush()
                }
            } catch (e: Exception) {
                if (running.get()) {
                    runOnUiThread {
                        status.text = "Transfer error: ${e.message}"
                    }
                }
            } finally {
                running.set(false)

                try {
                    if (recorder.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                        recorder.stop()
                    }
                } catch (_: Exception) {
                }

                try {
                    output?.close()
                } catch (_: Exception) {
                }

                try {
                    socket?.close()
                } catch (_: Exception) {
                }

                recorder.release()
                if (audioRecord === recorder) audioRecord = null

                runOnUiThread {
                    toggleButton.text = "Mic Transfer ON"
                    toggleButton.isEnabled = true
                    if (!isFinishing) {
                        if (!status.text.toString().startsWith("Transfer error:")) {
                            status.text = "Mic Transfer OFF"
                        }
                    }
                }
            }
        }.also { it.start() }
    }

    private fun stopMic() {
        running.set(false)
        toggleButton.isEnabled = false

        try {
            audioRecord?.stop()
        } catch (_: Exception) {
        }

        // Closing the socket unblocks a stalled write if necessary.
        recordingThread?.interrupt()
        recordingThread?.join(1000)
        recordingThread = null

        toggleButton.text = "Mic Transfer ON"
        toggleButton.isEnabled = true
        status.text = "Mic Transfer OFF"
    }

    override fun onDestroy() {
        if (running.get()) stopMic()
        super.onDestroy()
    }
}
