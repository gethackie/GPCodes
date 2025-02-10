from flask import Flask, request, render_template, send_file
import qrcode
from PIL import Image
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm

app = Flask(__name__)

# Ensure the uploads directory exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Path to the default NHS logo
DEFAULT_LOGO_PATH = os.path.join("static", "nhs_logo.png")

# Path to Montserrat font (you need to download the font file)
FONT_PATH = os.path.join("static", "Montserrat-SemiBold.ttf")

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        # Get data from the form
        data = request.form.get("data")
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        logo_file = request.files.get("logo")
        logo_size = request.form.get("logo_size", "medium")  # Small, Medium, Large

        if not data:
            return "Please enter data to generate a QR code."

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        # Add logo (default or custom)
        if logo_file:
            logo = Image.open(logo_file)
        else:
            logo = Image.open(DEFAULT_LOGO_PATH)

        # Convert logo to RGBA (to handle transparency)
        logo = logo.convert("RGBA")

        # Resize logo based on selected size
        qr_size = qr_img.size[0]
        if logo_size == "small":
            max_logo_size = int(qr_size * 0.15)  # 15% of QR code size
        elif logo_size == "large":
            max_logo_size = int(qr_size * 0.25)  # 25% of QR code size
        else:
            max_logo_size = int(qr_size * 0.2)  # 20% of QR code size (medium)

        # Calculate new size while preserving aspect ratio
        logo_ratio = logo.width / logo.height
        if logo.width > logo.height:
            new_width = max_logo_size
            new_height = int(max_logo_size / logo_ratio)
        else:
            new_height = max_logo_size
            new_width = int(max_logo_size * logo_ratio)

        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Add white background to the logo
        logo_with_bg = Image.new("RGBA", logo.size, "WHITE")
        logo_with_bg.paste(logo, (0, 0), logo)

        # Calculate position to paste logo (center of QR code)
        pos = (
            (qr_img.size[0] - logo_with_bg.size[0]) // 2,
            (qr_img.size[1] - logo_with_bg.size[1]) // 2
        )

        # Create a transparent layer for the logo
        transparent_logo = Image.new("RGBA", qr_img.size, (0, 0, 0, 0))
        transparent_logo.paste(logo_with_bg, pos)

        # Blend the logo with the QR code
        qr_img = Image.alpha_composite(qr_img.convert("RGBA"), transparent_logo)

        # Save QR code to a temporary file
        qr_img_path = os.path.join(app.config['UPLOAD_FOLDER'], "qr_code.png")
        qr_img.save(qr_img_path)

        # Generate PDF
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Set up styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="TitleStyle",
            fontName="Helvetica-Bold",
            fontSize=28,  # Larger font size for title
            alignment=TA_CENTER,
            spaceAfter=40,  # Increased space after title
            underline=True,  # Underline the title
        )
        description_style = ParagraphStyle(
            name="DescriptionStyle",
            fontName="Helvetica",
            fontSize=20,  # Larger font size for description
            alignment=TA_CENTER,
            leading=24,  # Increased line spacing
            spaceAfter=40,
        )
        footer_style = ParagraphStyle(
            name="FooterStyle",
            fontName="Helvetica",
            fontSize=12,
            alignment=TA_CENTER,
            spaceBefore=20,
        )

        # Add title (underlined)
        title_paragraph = Paragraph(title, title_style)
        title_paragraph.wrapOn(pdf, width - 100, height)
        title_paragraph.drawOn(pdf, 50, height - 100)

        # Add description (with increased line spacing and more space from title)
        description_paragraph = Paragraph(description, description_style)
        description_paragraph.wrapOn(pdf, width - 100, height)
        description_paragraph.drawOn(pdf, 50, height - 200)  # Adjusted position (more space)

        # Add QR code (centered at the bottom)
        qr_img_reader = ImageReader(qr_img_path)
        qr_width = 300
        qr_height = 300
        qr_x = (width - qr_width) / 2
        qr_y = 100  # Position at the bottom
        pdf.drawImage(qr_img_reader, qr_x, qr_y, width=qr_width, height=qr_height)

        # Add footer
        footer_text = "Created using Patient Link QR tool"
        footer_paragraph = Paragraph(footer_text, footer_style)
        footer_paragraph.wrapOn(pdf, width - 100, height)
        footer_paragraph.drawOn(pdf, 50, 50)  # Position at the bottom

        # Save PDF
        pdf.save()
        buffer.seek(0)

        # Clean up temporary file
        os.remove(qr_img_path)

        # Return the PDF for preview
        return send_file(buffer, mimetype="application/pdf", as_attachment=False)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)