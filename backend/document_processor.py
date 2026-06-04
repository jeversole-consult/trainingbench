"""
Document processing utilities for extracting text from various file formats.
Supports PDF, MS Word (.docx), MS Excel (.xlsx), and images with OCR.
"""

import io
from typing import List, Dict
from pathlib import Path

# PDF processing
import pypdf
import pdfplumber
from pdf2image import convert_from_bytes

# MS Office processing
from docx import Document
import openpyxl
import pandas as pd

# OCR processing
import pytesseract
from PIL import Image


class DocumentProcessor:
    """Handles extraction of text content from various document formats."""

    @staticmethod
    def process_pdf(file_content: bytes, filename: str, use_ocr: bool = False) -> Dict[str, any]:
        """
        Extract text from PDF files using both pypdf and pdfplumber, with optional OCR fallback.

        Args:
            file_content: Raw bytes of the PDF file
            filename: Name of the file
            use_ocr: If True, uses OCR for scanned PDFs or as fallback

        Returns:
            Dictionary containing extracted text and metadata
        """
        text_content = []
        used_ocr = False

        try:
            # Try pdfplumber first (better for complex PDFs)
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                    elif use_ocr:
                        # Use OCR if no text found on this page
                        used_ocr = True
                        text_content.append(f"--- Page {page_num} (OCR) ---")
        except Exception as e:
            # Fallback to pypdf
            try:
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                    elif use_ocr:
                        used_ocr = True
                        text_content.append(f"--- Page {page_num} (OCR) ---")
            except Exception as fallback_error:
                if not use_ocr:
                    raise ValueError(f"Failed to process PDF: {str(e)}, Fallback error: {str(fallback_error)}")

        # If we need OCR or extracted minimal text, use OCR on the entire PDF
        if use_ocr and (not text_content or used_ocr):
            try:
                images = convert_from_bytes(file_content)
                text_content = []
                for page_num, image in enumerate(images, 1):
                    ocr_text = pytesseract.image_to_string(image)
                    if ocr_text.strip():
                        text_content.append(f"--- Page {page_num} (OCR) ---\n{ocr_text}")
                used_ocr = True
            except Exception as ocr_error:
                if not text_content:
                    raise ValueError(f"Failed to process PDF with OCR: {str(ocr_error)}")

        return {
            "filename": filename,
            "type": "pdf",
            "content": "\n\n".join(text_content),
            "page_count": len(text_content),
            "used_ocr": used_ocr
        }

    @staticmethod
    def process_docx(file_content: bytes, filename: str) -> Dict[str, any]:
        """
        Extract text from MS Word (.docx) files.

        Args:
            file_content: Raw bytes of the Word file
            filename: Name of the file

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            doc = Document(io.BytesIO(file_content))

            # Extract paragraphs
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

            # Extract tables
            tables_content = []
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells]
                    table_text.append(" | ".join(row_text))
                if table_text:
                    tables_content.append("\n".join(table_text))

            content_parts = paragraphs
            if tables_content:
                content_parts.append("\n\n--- Tables ---\n")
                content_parts.extend(tables_content)

            return {
                "filename": filename,
                "type": "docx",
                "content": "\n\n".join(content_parts),
                "paragraph_count": len(paragraphs),
                "table_count": len(doc.tables)
            }
        except Exception as e:
            raise ValueError(f"Failed to process DOCX file: {str(e)}")

    @staticmethod
    def process_xlsx(file_content: bytes, filename: str) -> Dict[str, any]:
        """
        Extract text from MS Excel (.xlsx) files.

        Args:
            file_content: Raw bytes of the Excel file
            filename: Name of the file

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            # Read Excel file with pandas
            excel_file = pd.ExcelFile(io.BytesIO(file_content))

            sheets_content = []
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)

                # Convert dataframe to text
                sheet_text = f"--- Sheet: {sheet_name} ---\n"
                sheet_text += df.to_string(index=False)
                sheets_content.append(sheet_text)

            return {
                "filename": filename,
                "type": "xlsx",
                "content": "\n\n".join(sheets_content),
                "sheet_count": len(excel_file.sheet_names)
            }
        except Exception as e:
            raise ValueError(f"Failed to process XLSX file: {str(e)}")

    @staticmethod
    def process_text(file_content: bytes, filename: str) -> Dict[str, any]:
        """
        Extract text from plain text files.

        Args:
            file_content: Raw bytes of the text file
            filename: Name of the file

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            # Try UTF-8 first, fall back to latin-1 if that fails
            try:
                text = file_content.decode('utf-8')
                encoding = 'utf-8'
            except UnicodeDecodeError:
                text = file_content.decode('latin-1')
                encoding = 'latin-1'

            # Count lines and characters
            lines = text.split('\n')
            line_count = len(lines)
            char_count = len(text)

            return {
                "filename": filename,
                "type": "text",
                "content": text,
                "line_count": line_count,
                "char_count": char_count,
                "encoding": encoding
            }
        except Exception as e:
            raise ValueError(f"Failed to process text file: {str(e)}")

    @staticmethod
    def process_image(file_content: bytes, filename: str) -> Dict[str, any]:
        """
        Extract text from image files using OCR (Tesseract).

        Args:
            file_content: Raw bytes of the image file
            filename: Name of the file

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            image = Image.open(io.BytesIO(file_content))

            # Perform OCR
            text = pytesseract.image_to_string(image)

            # Get additional image info
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidence = sum(int(c) for c in data['conf'] if c != '-1') / len([c for c in data['conf'] if c != '-1']) if data['conf'] else 0

            return {
                "filename": filename,
                "type": "image",
                "content": text,
                "image_size": f"{image.width}x{image.height}",
                "image_format": image.format,
                "ocr_confidence": round(confidence, 2)
            }
        except Exception as e:
            raise ValueError(f"Failed to process image file: {str(e)}")

    @classmethod
    def process_file(cls, file_path_or_content, filename: str = None, use_ocr: bool = False) -> Dict[str, any]:
        """
        Process a file based on its extension and extract text content.

        Args:
            file_path_or_content: Either raw bytes of the file or a file path string
            filename: Name of the file (required if file_path_or_content is bytes)
            use_ocr: If True, enables OCR for PDFs and images

        Returns:
            Dictionary containing extracted text and metadata

        Raises:
            ValueError: If file type is not supported
        """
        # Handle both file paths and bytes
        if isinstance(file_path_or_content, str):
            # It's a file path
            file_path = Path(file_path_or_content)
            with open(file_path, 'rb') as f:
                file_content = f.read()
            filename = filename or file_path.name
        else:
            # It's bytes content
            file_content = file_path_or_content
            if not filename:
                raise ValueError("filename is required when passing bytes content")

        extension = Path(filename).suffix.lower()

        # Image extensions that support OCR
        image_extensions = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif'}

        if extension in ('.txt', '.md', '.markdown'):
            return cls.process_text(file_content, filename)
        elif extension in image_extensions:
            return cls.process_image(file_content, filename)
        elif extension == '.pdf':
            return cls.process_pdf(file_content, filename, use_ocr=use_ocr)
        elif extension == '.docx':
            return cls.process_docx(file_content, filename)
        elif extension == '.xlsx':
            return cls.process_xlsx(file_content, filename)
        else:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: .txt, .md, .markdown, .pdf, .docx, .xlsx, {', '.join(image_extensions)}"
            )
