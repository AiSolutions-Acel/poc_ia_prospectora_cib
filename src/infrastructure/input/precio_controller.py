from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.domain.models.precio import Precio
from src.application.services.get_precios import GetPreciosUseCase

router = APIRouter(prefix="/precios", tags=["Mock"])

def get_use_case():
    from main import get_precios_use_case
    return get_precios_use_case

@router.get("", response_model=List[Precio])
async def list_precios(use_case: GetPreciosUseCase = Depends(get_use_case)):
    """Retorna los precios mockeados de las carreras de Cibertec."""
    return use_case.get_all()

@router.get("/{precio_id}", response_model=Precio)
async def get_precio(precio_id: int, use_case: GetPreciosUseCase = Depends(get_use_case)):
    """Retorna un precio específico por ID."""
    precio = use_case.get_by_id(precio_id)
    if precio is None:
        raise HTTPException(status_code=404, detail=f"Precio con id={precio_id} no encontrado")
    return precio
