from app.tools.base import ToolHandler, ProcessingContext
from app.tools.registry import TOOL_REGISTRY, get_tool_handler
from app.tools.merge import MergePDFHandler
from app.tools.split import SplitPDFHandler
from app.tools.compress import CompressPDFHandler
from app.tools.rotate import RotatePDFHandler
from app.tools.watermark import WatermarkPDFHandler
from app.tools.page_numbers import PageNumbersPDFHandler
from app.tools.protect import ProtectPDFHandler
from app.tools.unlock import UnlockPDFHandler
from app.tools.extract_pages import ExtractPagesPDFHandler
from app.tools.organize import OrganizePDFHandler
from app.tools.pdf_to_jpg import PdfToJpgPDFHandler
from app.tools.jpg_to_pdf import JpgToPdfPDFHandler
from app.tools.repair import RepairPDFHandler

__all__ = [
    "ToolHandler",
    "ProcessingContext",
    "TOOL_REGISTRY",
    "get_tool_handler",
    "MergePDFHandler",
    "SplitPDFHandler",
    "CompressPDFHandler",
    "RotatePDFHandler",
    "WatermarkPDFHandler",
    "PageNumbersPDFHandler",
    "ProtectPDFHandler",
    "UnlockPDFHandler",
    "ExtractPagesPDFHandler",
    "OrganizePDFHandler",
    "PdfToJpgPDFHandler",
    "JpgToPdfPDFHandler",
    "RepairPDFHandler",
]
