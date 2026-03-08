import fitz
import time
import concurrent.futures

def render_page(doc_path, page_idx, zoom=1.5):
    # have to open a new handle for every thread
    doc = fitz.open(doc_path)
    page = doc[page_idx]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.invert_irect(pix.irect)
    doc.close()
    return page_idx, pix.tobytes("png")  # return bytes so it can be safely passed between threads

def test_sequential(doc_path):
    start = time.time()
    src = fitz.open(doc_path)
    dst = fitz.open()
    for page_idx in range(len(src)):
        page = src[page_idx]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.invert_irect(pix.irect)
        rect = page.rect
        new_page = dst.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)
    dst.close()
    src.close()
    print(f"Sequential: {time.time() - start:.2f}s")

def test_parallel(doc_path):
    start = time.time()
    src = fitz.open(doc_path)
    num_pages = len(src)
    rects = [src[i].rect for i in range(num_pages)]
    src.close()
    
    dst = fitz.open()
    
    # Pre-make pages
    for r in rects:
        dst.new_page(width=r.width, height=r.height)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(render_page, doc_path, i): i for i in range(num_pages)}
        
        for future in concurrent.futures.as_completed(futures):
            page_idx, png_bytes = future.result()
            dst[page_idx].insert_image(dst[page_idx].rect, stream=png_bytes)
            
    dst.close()
    print(f"Parallel: {time.time() - start:.2f}s")

if __name__ == "__main__":
    doc = fitz.open()
    for _ in range(10):  # create a synthetic 10 page pdf
         doc.new_page()
    doc.save("test_10.pdf")
    doc.close()
    
    test_sequential("test_10.pdf")
    test_parallel("test_10.pdf")
