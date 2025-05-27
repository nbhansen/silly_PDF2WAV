import google.generativeai as genai

class LLMProcessor:
    """
    Handles text cleaning using Google's Generative AI (Gemini).
    """
    def __init__(self, api_key):
        """
        Initializes the LLMProcessor and configures the Google AI client.

        Args:
            api_key (str): The Google AI API key for Gemini.
        """
        self.api_key = api_key
        self.model = None
        
        if self.api_key and self.api_key != "YOUR_GOOGLE_AI_API_KEY" and self.api_key.strip() != "":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash') 
                print("LLMProcessor: Google AI API (Gemini) configured successfully.")
            except Exception as e:
                print(f"LLMProcessor: Error configuring Google AI API: {e}")
                print("LLM cleaning will likely fail. Ensure your API key is correct and the API is enabled.")
        else:
            print("LLMProcessor: Google AI API Key not provided or is placeholder. LLM cleaning will be skipped.")

    def clean_text(self, text_to_clean):
        """
        Sends text to the Gemini model for cleaning based on predefined rules.

        Args:
            text_to_clean (str): The raw text string to be cleaned.

        Returns:
            str: The cleaned text from the LLM, or the original text/error message if cleaning fails or is skipped.
        """
        if not self.model:
            print("LLMProcessor: Model not initialized (check API Key). Skipping cleaning.")
            return "LLM cleaning skipped: Model not initialized."
        
        if not text_to_clean or text_to_clean.strip() == "" or \
           text_to_clean.startswith("Could not convert") or \
           text_to_clean.startswith("No text could be extracted") or \
           text_to_clean.startswith("Error during OCR") or \
           text_to_clean.startswith("Tesseract OCR engine not found"):
            print("LLMProcessor: Skipping cleaning due to empty or error text from upstream process.")
            return text_to_clean

        print(f"LLMProcessor: Sending text (length: {len(text_to_clean)} chars) to Gemini for cleaning.")
        
        # Revised prompt with more emphasis on spacing and natural language output
        prompt = f"""Your primary goal is to clean the following text, extracted from an academic research paper. The cleaned text should be highly readable and well-suited for text-to-speech (TTS) conversion.

**Key Cleaning Tasks (Remove these elements):**
- Headers and Footers: This includes page numbers, running titles, journal names, conference names, and dates that appear consistently at the top or bottom of pages.
- Line Numbers: If present in the margins.
- Marginalia or Side Notes: Any comments or notes found in the margins.
- Watermarks or Stamps: Text like "Draft," "Confidential," or institutional logos/stamps.
- Artifacts from Scanning: Random specks, stray lines, or heavily distorted characters that are clearly not part of the intended text.
- Repeated Copyright or Licensing Information: Especially if it appears on every page or in a boilerplate manner.
- Extraneous Punctuation or Symbols: Symbols or punctuation that are likely errors from the OCR process and do not contribute to the meaning.

**Core Content Preservation (Focus on these):**
- Preserve all text that would be read aloud in an ebook, including all paragraphs and their intended structure.
- Skip in-text citations (e.g., [1], (Author, 2023)).
- Skip mathematical formulas and equations if present.

**Crucial for Readability and TTS (Pay close attention to these):**
- **Maintain or Reconstruct Natural Spacing:** Ensure there is a single proper space between all words. Ensure appropriate single spacing follows all punctuation marks (e.g., a period, comma, colon, semicolon should be followed by a space, unless it's part of a standard abbreviation like "e.g.").
- **Handle Hyphenated Words:** If words are hyphenated across line breaks in the input (e.g., "effec-\\ntive"), correctly join them into single words (e.g., "effective") in the output. This single word should then be followed by appropriate spacing.
- **Avoid Run-on Words:** The final output must be composed of clearly separated words and sentences. Do not merge words that should be distinct.
- The output must be grammatically correct, well-formed English text, structured into natural paragraphs suitable for reading aloud.

**Cautious Removal (Use best judgment to maintain readability of primary content):**
- Figure Captions and Table Titles: If these are interspersed in a way that breaks the flow of the main narrative, try to remove them. However, if they are embedded and provide crucial context, it might be better to keep them.
- Footnote/Endnote Markers: Keep markers like [1] or ^2 within the text if they are part of the original flow. However, remove the full text of footnotes or endnotes if they have been erroneously pulled into the main text flow by OCR.

Here is the text to clean:
---
{text_to_clean}
---
Cleaned text:"""
        try:
            response = self.model.generate_content(prompt)
            print("LLMProcessor: LLM (Gemini) response received.")
            
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                cleaned_text = response.candidates[0].content.parts[0].text
                # Basic post-check for common run-on issues (very simple)
                # A more robust post-processor might be needed for complex cases.
                # Example: trying to insert a space if a lowercase is followed by an uppercase (CamelCase)
                # import re
                # cleaned_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned_text)
                return cleaned_text
            else:
                feedback_info = ""
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    feedback_info += f" Prompt Feedback: {response.prompt_feedback}."
                if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'finish_reason'):
                     feedback_info += f" Finish Reason: {response.candidates[0].finish_reason}."
                     if hasattr(response.candidates[0], 'safety_ratings'):
                         feedback_info += f" Safety Ratings: {response.candidates[0].safety_ratings}."
                print(f"LLMProcessor: LLM response issue.{feedback_info if feedback_info else ' Unexpected structure or content possibly blocked.'}")
                return f"Error: LLM response issue.{feedback_info if feedback_info else ' Unexpected structure or content possibly blocked.'}"
        except Exception as e:
            print(f"LLMProcessor: Error during LLM cleaning with Gemini: {e}")
            return f"Error during LLM cleaning with Gemini: {str(e)}"
