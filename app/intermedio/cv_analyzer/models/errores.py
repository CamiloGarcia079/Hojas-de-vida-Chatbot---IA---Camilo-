"""Errores controlados. La interfaz los muestra tal cual al usuario, por eso sus
mensajes están escritos para una persona y no para un programador."""


class ErrorAnalizador(Exception):
    """Base de todos los errores conocidos del analizador."""


class ErrorPDF(ErrorAnalizador):
    """El archivo no se pudo leer o no tiene texto seleccionable."""


class ErrorEntrada(ErrorAnalizador):
    """Faltan datos o no tienen el largo mínimo (CV o descripción del puesto)."""


class ErrorEvaluacion(ErrorAnalizador):
    """El modelo no respondió o su respuesta no cumple el contrato AnalisisCV."""
