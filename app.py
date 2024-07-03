from flask import Flask, request, send_from_directory, jsonify, render_template, send_file
import fitz  # PyMuPDF
from PIL import Image
import os
from werkzeug.utils import secure_filename
import zipfile
from io import BytesIO

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output_images'
PDF_OUTPUT_FOLDER = 'output_pdfs'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['PDF_OUTPUT_FOLDER'] = PDF_OUTPUT_FOLDER

# Ensure the upload and output directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(PDF_OUTPUT_FOLDER, exist_ok=True)

def pdf_to_jpg(pdf_path, output_folder):
    pdf_document = fitz.open(pdf_path)
    output_images = []
    
    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_path = f"{output_folder}/{os.path.basename(pdf_path)}_page_{page_number + 1}.jpg"
        image.save(image_path, "JPEG")
        output_images.append(image_path)
    
    return output_images

def jpg_to_pdf(image_paths, output_folder, output_filename):
    images = [Image.open(img).convert('RGB') for img in image_paths]
    pdf_path = os.path.join(output_folder, output_filename)
    images[0].save(pdf_path, save_all=True, append_images=images[1:])
    return pdf_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('files[]')
    if not files:
        return jsonify({"error": "No selected files"}), 400
    
    all_images = []
    
    for file in files:
        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)
            
            output_images = pdf_to_jpg(pdf_path, app.config['OUTPUT_FOLDER'])
            all_images.extend(output_images)
    
    image_names = [os.path.basename(img) for img in all_images]
    return jsonify({"images": image_names}), 200

@app.route('/upload_images', methods=['POST'])
def upload_images():
    if 'files[]' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('files[]')
    if not files:
        return jsonify({"error": "No selected files"}), 400

    image_paths = []

    for file in files:
        if file and file.filename.endswith(('.jpg', '.jpeg', '.png')):
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)
            image_paths.append(image_path)

    if not image_paths:
        return jsonify({"error": "No valid image files"}), 400

    output_filename = "output.pdf"
    pdf_path = jpg_to_pdf(image_paths, app.config['PDF_OUTPUT_FOLDER'], output_filename)
    return jsonify({"pdf": os.path.basename(pdf_path)}), 200

@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/pdfs/<filename>')
def uploaded_pdf(filename):
    return send_from_directory(app.config['PDF_OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/download_zip')
def download_zip():
    output_folder = app.config['OUTPUT_FOLDER']
    zip_filename = "images.zip"
    
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for foldername, subfolders, filenames in os.walk(output_folder):
            for filename in filenames:
                if filename.endswith(".jpg"):
                    file_path = os.path.join(foldername, filename)
                    zf.write(file_path, os.path.basename(file_path))
    memory_file.seek(0)
    
    return send_file(memory_file, download_name=zip_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
