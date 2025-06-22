# Read-Along Disabled for Gemini TTS

## Summary
Read-along functionality has been cleanly disabled when Gemini TTS is selected, due to performance issues with long documents.

## Changes Made (5 lines total)

### 1. Frontend Disable (`templates/index.html`)
```html
<!-- Line 54: Disable checkbox for Gemini -->
<input type="checkbox" id="enable_read_along" name="enable_read_along" onchange="updateFormAction()" {{ 'disabled' if tts_engine == 'gemini' else '' }}>

<!-- Line 55: Add explanation text -->
<label for="enable_read_along" class="checkbox-label">📖 Enable Read-Along Mode (synchronized text highlighting){% if tts_engine == 'gemini' %} - Available with Piper TTS only{% endif %}</label>
```

### 2. Backend Protection (`app.py`)
```python
# Line 134: Pass TTS engine to template
return render_template('index.html', tts_engine=app_config.tts_engine.value)

# Lines 413-414: Block timing route for Gemini
if app_config.tts_engine.value == 'gemini':
    return "Read-along mode is not available with Gemini TTS. Please use regular upload or switch to Piper TTS."

# Line 270: Override timing in form processing
enable_timing = enable_timing and app_config.tts_engine.value != 'gemini'
```

## User Experience

### With Piper TTS
- Read-along checkbox available and functional
- Full read-along capability preserved

### With Gemini TTS  
- Read-along checkbox disabled with clear explanation
- Attempts to access timing route blocked with friendly error
- All other functionality works normally

## Benefits
- ✅ **Minimal Code**: Only 5 lines changed
- ✅ **Clean UX**: Clear messaging, no confusing failures
- ✅ **Fully Reversible**: Easy to undo if Gemini timing improves
- ✅ **Zero Code Removal**: All infrastructure preserved
- ✅ **Bulletproof**: Frontend + backend protection

## Preserved Functionality
- All Gemini TTS audio generation features
- All Piper TTS features including read-along
- Complete timing infrastructure for future use
- Easy to re-enable Gemini read-along if performance improves