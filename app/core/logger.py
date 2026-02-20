import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO"):
    """
    Logging para toda la aplicación.
    
    Crea:
    - Logs en consola (stdout) para desarrollo
    - Logs en archivo para producción
    - Formato estandarizado con timestamps
    """
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_format = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola (desarrollo)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(log_format)
    
    # Handler para archivo (producción)
    file_handler = logging.FileHandler(
        filename=log_dir / "app.log",
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    
    # Handler para errores críticos (archivo separado)
    error_handler = logging.FileHandler(
        filename=log_dir / "errors.log",
        mode='a',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    root_logger.handlers.clear()
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    
    logging.info("Sistema de logging inicializado")