import fitz

def test_text_preservation(doc_path):
    doc = fitz.open(doc_path)
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pix.invert_irect(pix.irect)
        page.insert_image(page.rect, pixmap=pix, overlay=True)
    doc.save("tests/text_test.pdf", garbage=4, deflate=True)
    doc.close()

if __name__ == "__main__":
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello Searchable World", fontsize=24)
    doc.save("tests/text_source.pdf")
    doc.close()
    
    test_text_preservation("tests/text_source.pdf")
    
    # Verify if text is still there
    doc = fitz.open("tests/text_test.pdf")
    page = doc[0]
    print("Extracted Text:", repr(page.get_text()))
    doc.close()
