# Configuration Guide

This document describes all configuration options for the PDF to Audio converter.

## Configuration Methods

The application supports two configuration methods:

1. **YAML Configuration (Recommended)** - Structured configuration file
2. **Environment Variables (Fallback)** - For containerized deployments

## YAML Configuration

### Getting Started

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

### Configuration Structure

The YAML configuration is organized into logical sections:

```yaml
# Application settings
app:
  name: "PDF to Audio Converter"
  debug: false
  host: "0.0.0.0"
  port: 5000

# API Keys and Secrets
secrets:
  google_ai_api_key: ""  # Required for Gemini TTS/LLM

# TTS Engine Configuration
tts:
  engine: "piper"  # or "gemini"
  
  piper:
    model_name: "en_US-lessac-medium"
    models_dir: "piper_models"
    length_scale: 1.0
    
  gemini:
    model_name: "gemini-2.5-flash-preview-tts"
    voice_name: "Kore"  # Options: Kore, Charon, Aoede, Leda
    min_request_interval: 2.0
    use_measurement_mode: false

# Text Processing
text_processing:
  document_type: "research_paper"  # research_paper, literature_review, general
  enable_text_cleaning: true
  enable_ssml: true
  chunk_size: 4000

# File Management
files:
  upload_folder: "uploads"
  audio_folder: "audio_outputs"
  max_file_size_mb: 20
  allowed_extensions: ["pdf"]
  
  cleanup:
    enabled: true
    max_file_age_hours: 24.0
    auto_cleanup_interval_hours: 6.0
    max_disk_usage_mb: 500
```

### Key Features

- **Type Safety**: All values are properly parsed (booleans, integers, floats)
- **Validation**: Range checking and required field validation
- **Defaults**: Sensible defaults for all optional settings
- **No Environment Fallback**: Pure YAML configuration without env var pollution

## Environment Variables

When `config.yaml` is not present, the application falls back to environment variables:

### Core Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TTS_ENGINE` | TTS engine selection | `piper` | `gemini` |
| `GOOGLE_AI_API_KEY` | Google AI API key | - | Your API key |
| `DOCUMENT_TYPE` | Document content type | `research_paper` | `literature_review` |
| `ENABLE_TEXT_CLEANING` | LLM text cleaning | `True` | `False` |
| `ENABLE_SSML` | SSML enhancement | `True` | `False` |

### TTS Engine Settings

#### Piper (Local)
| Variable | Description | Default |
|----------|-------------|---------|
| `PIPER_MODEL_NAME` | Voice model | `en_US-lessac-medium` |
| `PIPER_MODELS_DIR` | Model storage | `piper_models` |
| `PIPER_LENGTH_SCALE` | Speech speed | `1.0` |

#### Gemini (Cloud)
| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_VOICE_NAME` | Voice selection | `Kore` |
| `GEMINI_MIN_REQUEST_INTERVAL` | Rate limiting | `2.0` |
| `GEMINI_USE_MEASUREMENT_MODE` | Precise timing | `False` |

### File Management

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_FILE_CLEANUP` | Auto cleanup | `True` |
| `MAX_FILE_AGE_HOURS` | File retention | `24.0` |
| `MAX_DISK_USAGE_MB` | Disk limit | `1000` |
| `UPLOAD_FOLDER` | Upload directory | `uploads` |
| `AUDIO_FOLDER` | Output directory | `audio_outputs` |

### Audio Processing

| Variable | Description | Options |
|----------|-------------|---------|
| `AUDIO_BITRATE` | MP3 quality | `64k`, `128k`, `192k`, `320k` |
| `AUDIO_SAMPLE_RATE` | Sample rate | `16000`, `22050`, `44100` |
| `MP3_CODEC` | Audio codec | `libmp3lame` |

### Advanced Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OCR_LANGUAGE` | Tesseract language | `eng` |
| `OCR_DPI` | OCR resolution | `300` |
| `CHUNK_SIZE` | Text chunk size | `20000` |
| `MAX_CONCURRENT_REQUESTS` | Parallel processing | `4` |

## Voice System Architecture

### Simplified Design
- **Single Voice**: Each session uses one voice (Gemini) or model (Piper)
- **Content-Aware**: Document type drives speech patterns, not voice selection
- **No Voice Personas**: Removed complex multi-voice JSON configuration

### Document Types

1. **research_paper**: Technical, precise narration
   - Emphasizes methodology and findings
   - Slower pace for complex terms
   - Clear pronunciation of acronyms

2. **literature_review**: Analytical, thoughtful delivery
   - Natural flow for narrative sections
   - Emphasis on critiques and synthesis
   - Balanced pacing

3. **general**: Natural, conversational style
   - Standard pacing
   - Minimal special emphasis
   - Good for most documents

## Configuration Loading

The configuration system follows this priority:

1. **YAML File** (`config.yaml`)
   - Loaded via `SystemConfig.from_yaml()`
   - Type validation and range checking
   - Clear error messages

2. **Environment Variables**
   - Loaded via `SystemConfig.from_env()`
   - Used when YAML not found
   - Same validation as YAML

## Use Cases

### Development Setup
```yaml
# config.yaml
app:
  debug: true
  
tts:
  engine: "piper"  # Fast local development
  
files:
  cleanup:
    enabled: false  # Keep files for debugging
```

### Production with Gemini
```yaml
# config.yaml
app:
  debug: false
  
secrets:
  google_ai_api_key: "your-production-key"
  
tts:
  engine: "gemini"
  gemini:
    voice_name: "Kore"
    use_measurement_mode: true  # For read-along features
    
files:
  cleanup:
    enabled: true
    max_file_age_hours: 6.0  # Aggressive cleanup
    max_disk_usage_mb: 2000
```

### Multi-language Support
```yaml
# config.yaml
ocr:
  language: "fra"  # French OCR
  
text_processing:
  document_type: "general"  # Works across languages
```

## Testing Configuration

### Verify YAML Loading
```python
from application.config.system_config import SystemConfig

# Test YAML loading
config = SystemConfig.from_yaml('config.yaml')
config.print_summary()
```

### Check Specific Settings
```python
# Check TTS engine
print(f"TTS Engine: {config.tts_engine.value}")

# Check voice settings
if config.tts_engine.value == 'gemini':
    print(f"Voice: {config.gemini_voice_name}")
else:
    print(f"Model: {config.piper_model_name}")
```

## Migration from Environment Variables

To migrate from environment variables to YAML:

1. **Export current config**:
   ```bash
   python -c "
   from application.config.system_config import SystemConfig
   config = SystemConfig.from_env()
   # Manually create YAML from config values
   "
   ```

2. **Create config.yaml** based on `config.example.yaml`

3. **Test configuration**:
   ```bash
   python app.py
   # Should show: "✅ Loaded configuration from config.yaml"
   ```

## Troubleshooting

### Common Issues

1. **YAML parsing errors**:
   - Check for proper indentation (spaces, not tabs)
   - Validate with: `python -m yaml config.yaml`
   - Look for missing quotes around strings

2. **Type conversion errors**:
   - Ensure numeric values aren't quoted
   - Use proper boolean values: `true/false` not `"true"/"false"`

3. **Missing required fields**:
   - `tts.engine` is required (defaults to 'piper' if missing)
   - API keys required for Gemini features

### Validation Errors

The configuration system provides clear error messages:

```
ValueError: Invalid TTS engine 'invalid'. Must be one of: ['piper', 'gemini']
ValueError: GOOGLE_AI_API_KEY is required when TTS_ENGINE=gemini
ValueError: Value must be >= 1, got: 0
```

## Best Practices

1. **Use YAML for production** - Better organization and type safety
2. **Keep secrets separate** - Consider using environment variables just for secrets
3. **Version control** - Commit `config.example.yaml`, not `config.yaml`
4. **Document changes** - Update example when adding new settings
5. **Test configuration** - Validate settings before deployment

This configuration system provides flexibility while maintaining type safety and validation.