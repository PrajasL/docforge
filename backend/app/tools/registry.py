from app.core.errors import AppException
from app.tools.base import ToolHandler
from app.tools.compress import CompressPDFHandler
from app.tools.extract_pages import ExtractPagesPDFHandler
from app.tools.jpg_to_pdf import JpgToPdfPDFHandler
from app.tools.merge import MergePDFHandler
from app.tools.organize import OrganizePDFHandler
from app.tools.page_numbers import PageNumbersPDFHandler
from app.tools.pdf_to_jpg import PdfToJpgPDFHandler
from app.tools.protect import ProtectPDFHandler
from app.tools.repair import RepairPDFHandler
from app.tools.rotate import RotatePDFHandler
from app.tools.split import SplitPDFHandler
from app.tools.unlock import UnlockPDFHandler
from app.tools.watermark import WatermarkPDFHandler

TOOL_REGISTRY: dict[str, type[ToolHandler]] = {
    "merge": MergePDFHandler,
    "split": SplitPDFHandler,
    "compress": CompressPDFHandler,
    "rotate": RotatePDFHandler,
    "watermark": WatermarkPDFHandler,
    "page_numbers": PageNumbersPDFHandler,
    "protect": ProtectPDFHandler,
    "unlock": UnlockPDFHandler,
    "extract_pages": ExtractPagesPDFHandler,
    "extract-pages": ExtractPagesPDFHandler,
    "organize_pdf": OrganizePDFHandler,
    "organize-pdf": OrganizePDFHandler,
    "pdf_to_jpg": PdfToJpgPDFHandler,
    "pdf-to-jpg": PdfToJpgPDFHandler,
    "jpg_to_pdf": JpgToPdfPDFHandler,
    "jpg-to-pdf": JpgToPdfPDFHandler,
    "repair": RepairPDFHandler,
    "repair_pdf": RepairPDFHandler,
    "repair-pdf": RepairPDFHandler,
}


def get_tool_handler(tool_id: str) -> ToolHandler:
    """Retrieves an instantiated ToolHandler for the specified tool identifier."""
    handler_cls = TOOL_REGISTRY.get(tool_id.lower())
    if not handler_cls:
        raise AppException(
            status_code=400,
            code="UNKNOWN_TOOL",
            message=f"Tool '{tool_id}' is not recognized or not yet supported.",
        )
    return handler_cls()
