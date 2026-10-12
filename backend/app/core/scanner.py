import asyncio
import struct
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger

EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class ScannerException(AppException):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(status_code=status_code, code=code, message=message)


@dataclass
class ScanResult:
    is_clean: bool
    virus_name: str | None = None
    scanned: bool = True
    details: str | None = None


class ClamAVScanner:
    """
    Asynchronous ClamAV client implementing the standard clamd INSTREAM protocol.
    Streams document bytes to ClamAV over TCP/IP without writing temporary files to disk.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float | None = None,
        enabled: bool | None = None,
        fail_closed: bool | None = None,
    ):
        self.host = host or settings.CLAMAV_HOST
        self.port = port or settings.CLAMAV_PORT
        self.timeout = timeout if timeout is not None else settings.CLAMAV_TIMEOUT_SECONDS
        self.enabled = enabled if enabled is not None else settings.CLAMAV_ENABLED
        self.fail_closed = fail_closed if fail_closed is not None else settings.CLAMAV_FAIL_CLOSED

    async def ping(self) -> bool:
        """Sends zPING\\0 to ClamAV daemon and verifies PONG response."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=min(self.timeout, 3.0),
            )
            writer.write(b"zPING\0")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(128), timeout=min(self.timeout, 3.0))
            writer.close()
            await writer.wait_closed()
            return b"PONG" in response
        except Exception:
            return False

    async def scan_bytes(self, data: bytes, chunk_size: int = 65536) -> ScanResult:
        """
        Scans binary data using the ClamAV INSTREAM command.
        
        Security guarantees:
        1. Harmless EICAR test signature is always detected for deterministic antivirus testing.
        2. In production or when fail_closed is enabled, if ClamAV daemon is unreachable,
           raises 503 SCANNER_UNAVAILABLE rather than silently bypassing verification.
        3. Never sends data to third-party cloud APIs.
        """
        # 1. Deterministic EICAR test signature detection
        if EICAR_SIGNATURE in data:
            logger.warning("[ClamAV] Standard EICAR antivirus test file detected in upload")
            return ScanResult(
                is_clean=False,
                virus_name="Eicar-Test-Signature",
                scanned=True,
                details="EICAR standard antivirus test signature detected",
            )

        # 2. Check if ClamAV scanning is enabled
        if not self.enabled:
            logger.debug("[ClamAV] Scanner disabled by configuration; skipping daemon scan")
            return ScanResult(
                is_clean=True,
                virus_name=None,
                scanned=False,
                details="ClamAV disabled by configuration",
            )

        # 3. Stream data to ClamAV daemon via INSTREAM protocol
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except Exception as e:
            logger.error(f"[ClamAV] Failed to connect to scanner at {self.host}:{self.port}: {e}")
            if self.fail_closed or settings.ENVIRONMENT == "production":
                raise ScannerException(
                    code="SCANNER_UNAVAILABLE",
                    message="Malware scanner service is temporarily unavailable. Upload rejected for security.",
                    status_code=503,
                )
            return ScanResult(
                is_clean=True,
                virus_name=None,
                scanned=False,
                details=f"Scanner unavailable in non-production environment: {e}",
            )

        try:
            # Send INSTREAM command
            writer.write(b"zINSTREAM\0")
            await writer.drain()

            # Stream chunks
            offset = 0
            total_len = len(data)
            while offset < total_len:
                chunk = data[offset : offset + chunk_size]
                writer.write(struct.pack(">I", len(chunk)) + chunk)
                await writer.drain()
                offset += len(chunk)

            # Terminator (0-length chunk)
            writer.write(struct.pack(">I", 0))
            await writer.drain()

            # Read result
            raw_response = await asyncio.wait_for(reader.read(1024), timeout=self.timeout)
            response = raw_response.decode("utf-8", errors="replace").strip()

            logger.info(f"[ClamAV] Scan response: {response}")

            if "FOUND" in response:
                # Format: stream: <virus_name> FOUND
                virus = "Malware"
                parts = response.split()
                if len(parts) >= 3 and parts[-1] == "FOUND":
                    virus = parts[-2]
                logger.warning(f"[ClamAV] Threat detected: {virus}")
                return ScanResult(
                    is_clean=False,
                    virus_name=virus,
                    scanned=True,
                    details=f"Threat detected: {virus}",
                )

            if "ERROR" in response:
                logger.error(f"[ClamAV] Scan error returned by daemon: {response}")
                if self.fail_closed or settings.ENVIRONMENT == "production":
                    raise ScannerException(
                        code="SCANNER_ERROR",
                        message="Malware scanner encountered an error while scanning the file.",
                        status_code=503,
                    )
                return ScanResult(
                    is_clean=True,
                    virus_name=None,
                    scanned=False,
                    details=f"Scanner returned error: {response}",
                )

            return ScanResult(
                is_clean=True,
                virus_name=None,
                scanned=True,
                details="Clean",
            )

        except ScannerException:
            raise
        except Exception as e:
            logger.error(f"[ClamAV] Protocol error during streaming scan: {e}")
            if self.fail_closed or settings.ENVIRONMENT == "production":
                raise ScannerException(
                    code="SCANNER_UNAVAILABLE",
                    message="Malware scanner service is temporarily unavailable. Upload rejected for security.",
                    status_code=503,
                )
            return ScanResult(
                is_clean=True,
                virus_name=None,
                scanned=False,
                details=f"Scanner error in non-production environment: {e}",
            )
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def check_health(self) -> dict[str, Any]:
        """Check ClamAV daemon connectivity."""
        if not self.enabled:
            return {
                "status": "disabled",
                "enabled": False,
                "host": self.host,
                "port": self.port,
            }
        is_alive = await self.ping()
        return {
            "status": "connected" if is_alive else "disconnected",
            "enabled": True,
            "host": self.host,
            "port": self.port,
            "fail_closed": self.fail_closed,
        }


scanner = ClamAVScanner()


async def check_scanner_health() -> dict[str, Any]:
    return await scanner.check_health()
