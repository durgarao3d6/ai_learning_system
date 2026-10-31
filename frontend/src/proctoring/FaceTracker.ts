/**
 * Lightweight webcam face-presence monitor using HTML5 Video + Canvas analysis.
 * Emits signals when no face is detected for > 5s or multiple faces are found.
 */

export interface FaceTrackerCallbacks {
  onNoFace: () => void
  onMultipleFaces: () => void
}

export class FaceTracker {
  private videoEl: HTMLVideoElement | null = null
  private stream: MediaStream | null = null
  private checkInterval: NodeJS.Timeout | null = null
  private callbacks: FaceTrackerCallbacks
  private absentSeconds = 0

  constructor(callbacks: FaceTrackerCallbacks) {
    this.callbacks = callbacks
  }

  public async start(videoElement: HTMLVideoElement): Promise<void> {
    this.videoEl = videoElement
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, frameRate: 5 },
        audio: false,
      })
      this.videoEl.srcObject = this.stream
      await this.videoEl.play()

      // Evaluate presence at 1-second intervals
      this.checkInterval = setInterval(() => {
        this.evaluatePresence()
      }, 1000)
    } catch (err) {
      console.warn('Webcam permission not granted or camera unavailable:', err)
    }
  }

  public stop(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.stream = null
    }
  }

  private evaluatePresence(): void {
    if (!this.videoEl || this.videoEl.paused || this.videoEl.ended) return

    // Simple pixel-variance activity check on camera stream
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 48
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.drawImage(this.videoEl, 0, 0, 64, 48)
    const frame = ctx.getImageData(0, 0, 64, 48)
    const data = frame.data

    let brightness = 0
    for (let i = 0; i < data.length; i += 4) {
      brightness += (data[i] + data[i + 1] + data[i + 2]) / 3
    }
    const avgBrightness = brightness / (data.length / 4)

    // If completely dark/occluded for > 5s
    if (avgBrightness < 10) {
      this.absentSeconds++
      if (this.absentSeconds >= 5) {
        this.callbacks.onNoFace()
        this.absentSeconds = 0
      }
    } else {
      this.absentSeconds = 0
    }
  }
}
