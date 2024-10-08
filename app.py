from flask import Flask, request, send_file, render_template
from werkzeug.utils import secure_filename
import os
from io import BytesIO
import pymupdf 
from reportlab.lib.pagesizes import elevenSeventeen
from reportlab.pdfgen import canvas
from textwrap import wrap

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def extract_highlights(pdf_path):
    doc = pymupdf.open(pdf_path)
    highlights = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        for annot in page.annots():
            if annot.type[0] == 8:  
                rect = annot.rect
                expanded_rect = rect + (-2, -2, 2, 2)
                words = page.get_text("words", clip=expanded_rect)
                
                lines = []
                current_line = []
                current_y = None
                for w in words:
                    x0, y0, x1, y1, word = w[:5]  
                    if current_y is None:
                        current_y = y0
                    if abs(current_y - y0) > 2:  
                        lines.append(" ".join(current_line))
                        current_line = [word]
                        current_y = y0
                    else:
                        current_line.append(word)
                lines.append(" ".join(current_line))  

                extracted_text = "\n".join(lines)
                highlights.append(extracted_text.strip())

    return highlights


def create_highlight_pdf(highlights, output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=elevenSeventeen)
    width, height = elevenSeventeen
    margin = 40
    max_text_width = width - 2 * margin
    text_object = c.beginText(margin, height - margin)
    text_object.setFont("Helvetica", 12)
    line_height = 14  
    current_height = height - margin

    for highlight in highlights:
        if highlight:
            lines = highlight.split("\n")
            for line in lines:
                
                wrapped_lines = wrap(line, width=int(max_text_width / (c.stringWidth(" ", "Helvetica", 12))))
                
                for wrapped_line in wrapped_lines:
                    if current_height < margin + line_height:  
                        c.drawText(text_object)
                        c.showPage()
                        text_object = c.beginText(margin, height - margin)
                        text_object.setFont("Helvetica", 12)
                        current_height = height - margin
                    
                    text_object.textLine(wrapped_line)
                    current_height -= line_height

            
            if current_height >= margin + line_height:
                text_object.textLine("")
                current_height -= line_height

    c.drawText(text_object)
    c.showPage()
    c.save()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files:
        return "No file part", 400

    file = request.files['pdf_file']
    if file.filename == '':
        return "No selected file", 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        
        highlights = extract_highlights(file_path)

        output_pdf = BytesIO()
        create_highlight_pdf(highlights, output_pdf)
        output_pdf.seek(0)

        return send_file(output_pdf, as_attachment=True, download_name="extracted_highlights.pdf", mimetype='application/pdf')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

