# Configuration Guide

This document describes all configurable options for removing hardcoded dependencies in the PDF to Audio converter.

## Overview of Improvements

The application now supports extensive configuration to eliminate hardcoded dependencies and improve flexibility:

1. **Model Repository Configuration** - No longer tied to Hugging Face
2. **Voice Personas** - Fully customizable voice mapping
3. **Multi-language OCR** - Supports any Tesseract language
4. **Academic Terms** - Configurable domain-specific terminology
5. **Rate Limiting** - Dynamic API rate management
6. **File Extensions** - Configurable format support

## Configuration Files

### 1. Voice Personas (`config/voice_personas.json`)

Customize TTS voice mapping for different content types:

```json
{
  "narrator": {
    "voice": "Charon",
    "style": "informative and clear",
    "rate": "medium",
    "description": "Deep, authoritative voice for main narration"
  },
  "technical": {
    "voice": "Aoede",
    "style": "precise and measured", 
    "rate": "slower",
    "description": "Clear, professional voice for technical terms"
  }
}
```

**Environment Variable**: `VOICE_PERSONAS_CONFIG`

### 2. Academic Terms (`config/academic_terms_en.json`)

Define domain-specific vocabulary for different document types:

```json
{
  "research_paper": [
    "hypothesis", "methodology", "analysis", "correlation"
  ],
  "literature_review": [
    "synthesis", "critique", "meta-analysis"
  ],
  "technical_indicators": [
    "algorithm", "framework", "implementation"
  ]
}
```

**Environment Variable**: `ACADEMIC_TERMS_CONFIG`

### 3. Rate Limits (`config/rate_limits.json`)

Configure API rate limiting per TTS engine:

```json
{
  "rate_limits": {
    "GeminiTTSProvider": {
      "delay_seconds": 2.0,
      "max_retries": 3,
      "backoff_multiplier": 2.0,
      "max_delay_seconds": 30.0
    }
  }
}
```

**Environment Variable**: `RATE_LIMITS_CONFIG`

## Environment Variables

### New Configuration Options

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OCR_LANGUAGE` | Tesseract language code | `eng` | `fra`, `deu`, `spa` |
| `ALLOWED_EXTENSIONS` | Supported document formats | `pdf` | `pdf,docx,txt` |
| `AUDIO_EXTENSIONS` | Supported audio formats | `wav,mp3` | `wav,mp3,flac` |
| `PIPER_MODEL_REPOSITORY_URL` | Model repository URL | Hugging Face URL | Local mirror URL |
| `MODEL_CACHE_DIR` | Local model cache | `model_cache` | `/var/cache/models` |
| `VOICE_PERSONAS_CONFIG` | Voice config file path | `config/voice_personas.json` | Custom path |
| `ACADEMIC_TERMS_CONFIG` | Academic terms file | `config/academic_terms_en.json` | Language-specific |
| `RATE_LIMITS_CONFIG` | Rate limits file | `config/rate_limits.json` | Custom config |

### Audio Quality Settings

| Variable | Description | Options |
|----------|-------------|---------|
| `AUDIO_BITRATE` | MP3 quality | `64k`, `128k`, `192k`, `320k` |
| `AUDIO_SAMPLE_RATE` | Audio sample rate | `16000`, `22050`, `44100` |
| `MP3_CODEC` | Audio codec | `libmp3lame` |

### Timeout Settings

| Variable | Description | Range (seconds) |
|----------|-------------|-----------------|
| `TTS_TIMEOUT_SECONDS` | TTS generation timeout | 10-300 |
| `OCR_TIMEOUT_SECONDS` | OCR processing timeout | 5-120 |
| `FFMPEG_TIMEOUT_SECONDS` | Audio processing timeout | 30-600 |

## Use Cases

### 1. Air-gapped Deployment

```env
# Use local model repository
PIPER_MODEL_REPOSITORY_URL=http://local-mirror/piper-voices
MODEL_CACHE_DIR=/opt/models
```

### 2. Multi-language Support

```env
# French document processing
OCR_LANGUAGE=fra
ACADEMIC_TERMS_CONFIG=config/academic_terms_fr.json
```

### 3. High-quality Audio

```env
# Premium audio settings
AUDIO_BITRATE=320k
AUDIO_SAMPLE_RATE=44100
```

### 4. Custom Voice Mapping

Create `config/voice_personas_custom.json`:
```json
{
  "narrator": {
    "voice": "CustomVoice1",
    "style": "professional and warm",
    "rate": "medium"
  }
}
```

```env
VOICE_PERSONAS_CONFIG=config/voice_personas_custom.json
```

## Benefits

### Before (Hardcoded)
- ❌ Tied to Hugging Face repository
- ❌ English-only OCR
- ❌ Fixed voice personas
- ❌ Hardcoded academic terms
- ❌ Fixed API rate limits
- ❌ Limited file format support

### After (Configurable)
- ✅ Any model repository (local mirrors, S3, etc.)
- ✅ 100+ languages via Tesseract
- ✅ Fully customizable voice mapping
- ✅ Domain-specific terminology per language
- ✅ Dynamic rate limiting per API
- ✅ Extensible file format support

## Migration Guide

### Existing Deployments

1. **Copy configuration files** to your deployment:
   ```bash
   cp -r config/ /your/deployment/path/
   ```

2. **Update environment variables** in your `.env`:
   ```bash
   # Add new configuration options
   echo "OCR_LANGUAGE=eng" >> .env
   echo "PIPER_MODEL_REPOSITORY_URL=your_mirror_url" >> .env
   ```

3. **Customize configuration files** for your needs:
   - Edit voice personas for your use case
   - Add academic terms for your domain
   - Adjust rate limits for your API quotas

### Testing Configuration

Test your configuration changes:

```bash
# Test OCR language
python -c "from application.config.system_config import SystemConfig; print(SystemConfig.from_env().ocr_language)"

# Test voice personas loading
python -c "
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
provider = GeminiTTSProvider(api_key='test')
print(list(provider.voice_personas.keys()))
"
```

## Troubleshooting

### Configuration Loading Issues

1. **File not found errors**:
   - Ensure config files exist in specified paths
   - Check file permissions (readable by application)

2. **JSON parsing errors**:
   - Validate JSON syntax with `json.tool`
   - Check for trailing commas, missing quotes

3. **Environment variable issues**:
   - Verify `.env` file is loaded correctly
   - Check variable names (case-sensitive)

### Performance Considerations

1. **Rate limiting too aggressive**:
   - Increase `delay_seconds` in rate limits config
   - Reduce `max_concurrent_requests`

2. **Model download issues**:
   - Verify `PIPER_MODEL_REPOSITORY_URL` is accessible
   - Check network connectivity to model repository
   - Ensure sufficient disk space in `MODEL_CACHE_DIR`

This configuration system makes the application much more flexible and suitable for diverse deployment scenarios.