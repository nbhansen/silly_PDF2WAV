import google.generativeai as genai

class LLMProcessor:
    def __init__(self, api_key):
        """
        Initializes the LLMProcessor.
        Args:
            api_key (str): The Google AI API key.
        """
        self.api_key = api_key
        self.model = None
        # Configure genai only if the API key is valid and not the placeholder.
        if self.api_key and self.api_key != "YOUR_GOOGLE_AI_API_KEY" and self.api_key.strip() != "":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                print("LLMProcessor: Google AI API configured successfully.")
            except Exception as e:
                print(f"LLMProcessor: Error configuring Google AI API: {e}")
                # Potentially raise an error or set a flag indicating a problem
        else:
            print("LLMProcessor: API Key not provided or is placeholder. LLM cleaning will be skipped.")

    def clean_text(self, text_to_clean):
        """
        Uses Google's Generative AI to clean the provided text.
        Args:
            text_to_clean (str): The text string to be cleaned.
        Returns:
            str: The cleaned text, or an error message/original text if cleaning fails.
        """
        if not self.model:
            print("LLMProcessor: Model not initialized. Skipping cleaning.")
            return "LLM cleaning skipped: Model not initialized (check API Key)."
        
        # Check if the input text itself is an error message or empty
        if not text_to_clean or text_to_clean.strip() == "" or \
           text_to_clean.startswith("Could not convert") or \
           text_to_clean.startswith("No text could be extracted") or \
           text_to_clean.startswith("Error during OCR"):
            print("LLMProcessor: Skipping cleaning due to empty or error text from OCR stage.")
            return text_to_clean # Pass through the error or empty message

        print(f"LLMProcessor: Sending text for cleaning (length: {len(text_to_clean)} chars).")
        # Constructing the prompt based on user's requirements
        prompt = f"""Clean the following text extracted from an academic research paper. Remove the following elements:
- Headers and Footers (e.g., page numbers, running titles, journal names, dates)
- Line Numbers
- Marginalia or Side Notes
- Watermarks or Stamps (e.g., "Draft," "Confidential")
- Artifacts from Scanning (e.g., specks, lines, distorted characters that are not actual text)
- Repeated Copyright or Licensing Information if it appears on every page.
- Extraneous Punctuation or Symbols resulting from OCR errors.
- Any other non-textual elements that do not contribute to the main content such as linebreaks, page breaks, or excessive whitespace.
- Remove any figure captions or table titles that are not part of the main text.

Focus on preserving the main body of the text, including paragraphs, and the core content.
If figure captions or table titles are clearly identifiable and interrupt the main flow, you can remove them, but be cautious not to remove essential information if it's embedded.
Footnote/Endnote markers within the text (like [1], ^2) should generally be kept if they are part of the original text flow, but remove the full footnote text if it's mixed in.

the text will be fed to an text-to-speech model, so please ensure that the cleaned text is suitable for audio output.

Here is the text to clean:
---
{text_to_clean}
---
Cleaned text:"""
        try:
            response = self.model.generate_content(prompt)
            print("LLMProcessor: LLM response received.")
            
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                # Handle cases where the response structure is unexpected or content is missing/blocked
                feedback_info = ""
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    feedback_info += f" Prompt Feedback: {response.prompt_feedback}."
                if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'finish_reason'):
                     feedback_info += f" Finish Reason: {response.candidates[0].finish_reason}."
                     if hasattr(response.candidates[0], 'safety_ratings'):
                         feedback_info += f" Safety Ratings: {response.candidates[0].safety_ratings}."
                print(f"LLMProcessor: LLM response issue.{feedback_info if feedback_info else ' Unexpected structure or content blocked.'}")
                return f"Error: LLM response issue.{feedback_info if feedback_info else ' Unexpected structure or content blocked.'}"
        except Exception as e:
            print(f"LLMProcessor: Error during LLM cleaning: {e}")
            return f"Error during LLM cleaning: {str(e)}"
