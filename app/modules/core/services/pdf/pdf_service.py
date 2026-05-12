
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from jinja2 import Environment, FileSystemLoader,Template
from weasyprint import HTML
from app.modules.core.services.debug.debug_service import DebugService

class PdfService:
    
    def __init__(self, template_folder="templates"):
        """
        Initialize the PdfService with a template folder.
        :param template_folder: Path to the folder containing HTML templates.
        """
        # Convert the template folder to an absolute path
        self.template_folder = os.path.abspath(template_folder)
        self.env = Environment(loader=FileSystemLoader(self.template_folder))
        self.executor = ThreadPoolExecutor(max_workers=2)  # Limit concurrent PDF generation
        
    def render_template(self, template_name, data):
        """
        Render an HTML template with dynamic data.
        :param template_name: Name of the template file (e.g., "template.html").
        :param data: Dictionary of dynamic data to inject into the template.
        :return: Rendered HTML as a string.
        """
        template = self.env.get_template(template_name)
        return template.render(data)

    def generate_pdf_from_string(self, html_string, output_path):
        """
        Generate a PDF from an HTML string.
        :param html_string: HTML content as a string.
        :param output_path: Path to save the generated PDF.
        """
        HTML(string=html_string).write_pdf(output_path)

    def generate_pdf_from_template(self, template_name, data, output_path):
        """
        Generate a PDF from an HTML template with dynamic data.
        :param template_name: Name of the template file (e.g., "template.html").
        :param data: Dictionary of dynamic data to inject into the template.
        :param output_path: Path to save the generated PDF.
        """
        rendered_html = self.render_template(template_name, data)
        self.generate_pdf_from_string(rendered_html, output_path)
    
    def generate_pdf_from_template_html_str(self, template_html_str, data, output_path):
        """
        Generate a PDF from an HTML template string with dynamic data.
        :param template_html_str: HTML template content as a string.
        :param data: Dictionary of dynamic data to inject into the template.
        :param output_path: Path to save the generated PDF.
        """
        # Create a Jinja2 Template object from the HTML string
        template = Template(template_html_str)
        # Render the template with the provided data
        rendered_html = template.render(data)
        # Generate the PDF from the rendered HTML
        self.generate_pdf_from_string(rendered_html, output_path)

    def generate_pdf_from_url(self, url, output_path):
        """
        Generate a PDF from a URL.
        :param url: URL of the webpage to convert to PDF.
        :param output_path: Path to save the generated PDF.
        """
        HTML(url).write_pdf(output_path)

    async def generate_pdf_from_template_async(self, template_name, data, output_path):
        """
        Async version of generate_pdf_from_template that runs in a thread pool.
        :param template_name: Name of the template file (e.g., "template.html").
        :param data: Dictionary of dynamic data to inject into the template.
        :param output_path: Path to save the generated PDF.
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self.generate_pdf_from_template,
                template_name,
                data,
                output_path
            )
            return True
        except Exception as e:
            DebugService.app_debug_print(f"Failed to generate PDF async: {e}", True)
            raise

    def generate_pdf_background(self, template_name, data, output_path):
        """
        Background task method for generating PDFs without blocking the request.
        """
        try:
            DebugService.app_debug_print(f"Starting background PDF generation: {output_path}", True)
            self.generate_pdf_from_template(template_name, data, output_path)
            DebugService.app_debug_print(f"Background PDF generated successfully: {output_path}", True)
        except Exception as e:
            DebugService.app_debug_print(f"Failed to generate background PDF {output_path}: {e}", True)
            # Don't raise here as this is a background task