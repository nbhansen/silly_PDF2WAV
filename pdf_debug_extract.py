import pdfplumber

pdf_path = "uploads/3569898.pdf"  # Adjust path as needed

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    if len(pdf.pages) == 0:
        print("No pages found in PDF!")
    # Print the first 300 characters of the last 3 pages
    for i in range(-3, 0):
        page_num = len(pdf.pages) + i
        page = pdf.pages[i]
        text = page.extract_text()
        print(f"\n--- Page {page_num + 1} ---")
        if text:
            print(text[:300])
        else:
            print("[No text extracted from this page]")