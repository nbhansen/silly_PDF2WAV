#!/bin/bash
# Upgrade to modern Gemini API with TTS support

echo "🚀 Upgrading to modern Gemini API..."

# Stop the app if running
pkill -f "python app.py" 2>/dev/null || true

# Upgrade to latest versions
echo "📦 Installing latest dependencies..."
pip install --upgrade google-generativeai>=0.8.3
pip install --upgrade google-genai>=0.1.1

# Install gTTS as backup (optional but recommended)
pip install gtts>=2.5.0

# Verify installation
echo "✅ Verifying installation..."
python -c "
import google.generativeai as genai
print(f'✅ google-generativeai: {genai.__version__}')

try:
    from google.genai import types
    print('✅ google-genai types: Available')
except ImportError:
    print('❌ google-genai types: Not available')

if hasattr(genai, 'Client'):
    print('✅ genai.Client: Available')
else:
    print('❌ genai.Client: Not available')
"

echo ""
echo "🎯 Next steps:"
echo "1. Replace infrastructure/tts/gemini_tts_provider.py with the modern version"
echo "2. Replace requirements.txt with the modern version"  
echo "3. Restart your app: python app.py"
echo ""
echo "🎉 You'll now have access to:"
echo "   • High-quality Gemini 2.5 TTS"
echo "   • 6 different voices (Kore, Puck, Charon, etc.)"
echo "   • SSML and natural language style control"
echo "   • Better timing estimation for read-along"
