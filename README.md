## Features
* **Real-time Recording:** Capture high-quality audio directly through the terminal.
* **AI Transcription:** Uses the `base` Whisper model for robust speech-to-text conversion.
* **Fluency Scoring:** Calculates a percentage-based fluency score by comparing transcriptions against reference text.
* **Disfluency Detection:** Identifies specific errors including:
  * **Stutters/Insertions:** Extra sounds or repeated words.
  * **Mispronunciations:** Substituted words.
  * **Omissions:** Skipped words.
* **Targeted Feedback:** Generates a "Words You Struggled With" list to help users focus their practice.

---

## Technology Stack
* **Python 3.x**
* **OpenAI Whisper:** Speech-to-text transcription.
* **JiWER:** Speech-to-text alignment and Word Error Rate (WER) analysis.
* **PyAudio & Wave:** Audio recording and file processing.
* **Colorama:** Enhanced terminal visualization.

---
