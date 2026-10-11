import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Awaitable


@dataclass
class ProcessingContext:
    job_id: str
    input_files: List[Dict[str, Any]]
    config: Dict[str, Any]
    temp_dir: str
    progress_callback: Callable[[int], Awaitable[None]]


class ToolHandler(ABC):
    """Abstract base class that every PDF tool handler must implement."""

    tool_id: str
    display_name: str
    min_input_files: int
    max_input_files: int
    accepted_content_types: List[str]

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates tool-specific configuration. Raises AppException if invalid."""
        pass

    @abstractmethod
    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """
        Executes the tool processing logic.
        Returns a dict containing output file details:
        {
            "output_path": str,
            "filename": str,
            "size_bytes": int,
            "page_count": Optional[int],
            "sha256": Optional[str],
            ...
        }
        """
        pass
