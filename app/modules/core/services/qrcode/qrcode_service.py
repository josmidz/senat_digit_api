
import qrcode
import base64
from io import BytesIO
from PIL import Image

class QrcodeService:
    def __init__(self, version=1, box_size=10, border=4, error_correction=qrcode.constants.ERROR_CORRECT_L):
        """
        Initialize the QRCodeGenerator.
        
        :param version: QR code version (1 to 40, higher means more data).
        :param box_size: Size of each box in the QR code.
        :param border: Border size (in boxes).
        :param error_correction: Error correction level (L, M, Q, H).
        """
        self.version = version
        self.box_size = box_size
        self.border = border
        self.error_correction = error_correction
        
    def generate_qr_code(self, data, output_file=None, base64_encoded=False):
        """
        Generate a QR code.

        :param data: Data to encode in the QR code.
        :param output_file: File path to save the QR code image (optional).
        :param base64_encoded: If True, return the QR code as a Base64-encoded string.
        :return: PIL Image object or Base64-encoded string.
        """
        # Create QR code
        qr = qrcode.QRCode(
            version=self.version,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to file if output_file is provided
        if output_file:
            img.save(output_file)

        # Return Base64-encoded string if requested
        if base64_encoded:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{img_base64}"

        # Return PIL Image object
        return img