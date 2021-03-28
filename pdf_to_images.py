import os
from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_file):
    pages = convert_from_path(pdf_file, 500)
    print(type(pages[0]))
    return pages

pdf_file = './data/sample.pdf'
pages = convert_pdf_to_images(pdf_file)

def save_images(our_dir, pages):
    i = 0
    os.makedirs(os.path.join(our_dir), exist_ok=True)
    for page in pages:
        page.save(os.path.join(our_dir, 'out' + str(i) + '.jpg'), 'JPEG')
        i+=1

save_images("data/saved", pages)