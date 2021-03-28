from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_file):
    pages = convert_from_path(pdf_file, 500)
    print(type(pages[0]))
    return pages

#pdf_file = './data/sample.pdf'
#pages = convert_pdf_to_images(pdf_file)

def save_images(pages):
    i = 0
    for page in pages:
        page.save('out' + str(i) + '.jpg', 'JPEG')
        i+=1