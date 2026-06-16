from dataclasses import dataclass
from typing import Optional

@dataclass
class Precio:
    carrera: str
    tipo_carrera: str
    modalidad: str
    sede: str
    matricula: float
    cuota_mensual: float
    brochure: Optional[str] = None
    moneda: str = "PEN"
