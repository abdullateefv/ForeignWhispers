---
title: ForeignWhispers
emoji: 📈
colorFrom: green
colorTo: gray
sdk: streamlit
sdk_version: 1.29.0
app_file: app.py
pinned: false
license: unknown
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

```mermaid
graph TD
    SRT["SRT"] -->|/downloadVideo| Video["Video"]
    Video -->|/whisperTranscribe| WGT["Whisper Generated Transcript"]
    WGT -->|/translate| TWT["Translated Whisper Generated Transcript"]
    SRT -->|/translate-srt| TSRT["Translated SRT"]
    TSRT -->|/generateVideo| TV["Translated Video"]
```