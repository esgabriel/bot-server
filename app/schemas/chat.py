from pydantic import BaseModel, Field, validator

class PreguntaUsuario(BaseModel):
    texto: str = Field(
        ..., 
        min_length=1,
        max_length=1000,  # Limite de caracteres
        description="La pregunta del usuario"
    )
    site_id: str = Field(
        ..., 
        min_length=1,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",  # Solo caracteres seguros
        description="ID único del sitio"
    )
    
    @validator('texto')
    def texto_no_vacio(cls, v):
        if not v.strip():
            raise ValueError('El texto no puede estar vacío')
        return v.strip()

class RespuestaBot(BaseModel):
    respuesta: str
    fuentes: list[str] | None = None
    tiempo_respuesta: float | None = None  # tracking de performance
    site_id: str | None = None  # Confirmar qué sitio respondió