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

class MainActivity : Activity() {

    private var audioRecord: AudioRecord? = null
    private var recordingThread: Thread? = null
    private var isRecording = false

    private lateinit var status: TextView
    private lateinit var toggleButton: Button

    private val sampleRate = 48000

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
                if (isRecording) stopMic() else requestMicPermission()
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
            requestPermissions(
                arrayOf(Manifest.permission.RECORD_AUDIO), 100
            )
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
        recorder.startRecording()
        isRecording = true
        status.text = "Microphone capturing audio"
        toggleButton.text = "Mic Transfer OFF"

        recordingThread = Thread {
            val buffer = ShortArray(minBuffer / 2)

            while (isRecording) {
                val count = recorder.read(
                    buffer, 0, buffer.size,
                    AudioRecord.READ_BLOCKING
                )

                if (count < 0) break

                // Mono PCM samples are captured here.
                // USB streaming will be added next.
            }
        }.also { it.start() }
    }

    private fun stopMic() {
        isRecording = false

        try {
            audioRecord?.stop()
        } catch (_: IllegalStateException) {
        }

        recordingThread?.join(500)
        audioRecord?.release()
        audioRecord = null
        recordingThread = null

        status.text = "Mic Transfer OFF"
        toggleButton.text = "Mic Transfer ON"
    }

    override fun onDestroy() {
        if (isRecording) stopMic()
        super.onDestroy()
    }
}
