import pandas as pd
from typing import List, Optional
from src.domain.models.precio import Precio

class MockPrecioDb:
    def __init__(self, excel_path: str = "mock/BD IA Cibertec - (Lista de precios - News) (1).xlsx"):
        self.excel_path = excel_path
        self._load_data()

    def _load_data(self):
        try:
            df = pd.read_excel(self.excel_path)
            # Limpiar filas vacías sin nombre de carrera
            df = df.dropna(subset=['Carreras'])
            
            self.precios: List[Precio] = []
            
            for _, row in df.iterrows():
                try:
                    carrera = str(row.get('Carreras', '')).strip()
                    tipo = str(row.get('Tipo de carrera', '')).strip()
                    modalidad = str(row.get('Modalidad', '')).strip()
                    sede = str(row.get('Sede', '')).strip()
                    
                    # Convertir matrícula a float si es posible
                    matricula_val = row.get('Matrícula', 0.0)
                    try:
                        matricula = float(matricula_val) if pd.notna(matricula_val) else 0.0
                    except ValueError:
                        matricula = 0.0
                        
                    # Convertir cuota a float
                    cuota_val = row.get('Cuota 1', 0.0)
                    try:
                        cuota = float(cuota_val) if pd.notna(cuota_val) else 0.0
                    except ValueError:
                        cuota = 0.0
                        
                    brochure = str(row.get('Brochures', '')) if pd.notna(row.get('Brochures')) else None
                    if brochure == 'nan':
                        brochure = None
                        
                    self.precios.append(Precio(
                        carrera=carrera,
                        tipo_carrera=tipo,
                        modalidad=modalidad,
                        sede=sede,
                        matricula=matricula,
                        cuota_mensual=cuota,
                        brochure=brochure
                    ))
                except Exception as e:
                    print(f"Error parsing row: {e}")
                    
        except Exception as e:
            print(f"Error loading Excel: {e}")
            self.precios = []

    def get_all(self) -> List[Precio]:
        return getattr(self, 'precios', [])

    def buscar_cotizacion(self, carrera: str = "", tipo_carrera: str = "", modalidad: str = "", sede: str = "") -> List[Precio]:
        """
        Busca un precio que coincida de forma flexible con los criterios.
        """
        carrera_lower = carrera.lower().strip()
        tipo_lower = tipo_carrera.lower().strip()
        modalidad_lower = modalidad.lower().strip()
        sede_lower = sede.lower().strip()

        resultados = []
        for p in self.get_all():
            if carrera_lower in p.carrera.lower() and \
               tipo_lower in p.tipo_carrera.lower() and \
               modalidad_lower in p.modalidad.lower() and \
               sede_lower in p.sede.lower():
                resultados.append(p)
        return resultados
