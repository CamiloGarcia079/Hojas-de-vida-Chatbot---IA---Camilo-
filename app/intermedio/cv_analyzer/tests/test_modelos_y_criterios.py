"""Contrato AnalisisCV y reglas de evaluación (umbrales y pesos)."""
import pytest
from pydantic import ValidationError

from conftest import analisis_valido
from models.criterios import CRITERIOS, evaluacion_principal, recomendacion_final
from models.cv_model import AnalisisCV


# ------------------------------------------------------------------ AnalisisCV
def test_los_campos_son_los_del_taller():
    assert set(AnalisisCV.model_fields) == {
        "nombre_candidato", "experiencia_años", "habilidades_clave", "education",
        "experiencia_relevante", "fortalezas", "areas_mejora", "porcentaje_ajuste",
    }
    assert all(campo.is_required() for campo in AnalisisCV.model_fields.values())


def test_analisis_valido_se_crea():
    a = AnalisisCV(**analisis_valido())
    assert a.porcentaje_ajuste == 82 and a.experiencia_años == 3


@pytest.mark.parametrize("valor", [-1, 101, 150])
def test_porcentaje_fuera_de_rango_se_rechaza(valor):
    with pytest.raises(ValidationError):
        AnalisisCV(**analisis_valido(porcentaje_ajuste=valor))


@pytest.mark.parametrize("valor", [0, 100])
def test_porcentaje_en_los_limites_se_acepta(valor):
    assert AnalisisCV(**analisis_valido(porcentaje_ajuste=valor)).porcentaje_ajuste == valor


def test_experiencia_negativa_se_rechaza():
    with pytest.raises(ValidationError):
        AnalisisCV(**analisis_valido(experiencia_años=-2))


def test_falta_un_campo_se_rechaza():
    datos = analisis_valido()
    del datos["fortalezas"]  # el error del taller: el campo quedaba ausente
    with pytest.raises(ValidationError):
        AnalisisCV(**datos)


def test_listas_se_limpian_y_recortan():
    a = AnalisisCV(**analisis_valido(
        habilidades_clave=[" Java ", "java", "", "Git", "A", "B", "C", "D", "E", "F"],
        areas_mejora=["Inglés", "Python", "Kubernetes", "AWS", "Liderazgo"],
    ))
    assert a.habilidades_clave == ["Java", "Git", "A", "B", "C", "D", "E"]  # sin repetidos, máx. 7
    assert len(a.areas_mejora) == 4


def test_lista_vacia_se_rechaza():
    with pytest.raises(ValidationError):
        AnalisisCV(**analisis_valido(fortalezas=["  ", ""]))


def test_nombre_vacio_se_rechaza():
    with pytest.raises(ValidationError):
        AnalisisCV(**analisis_valido(nombre_candidato="   "))


# -------------------------------------------------------------------- criterios
def test_los_pesos_suman_100():
    assert sum(peso for _, peso in CRITERIOS) == 100
    assert dict(CRITERIOS)["Experiencia relevante"] == 40


@pytest.mark.parametrize("porcentaje, esperado", [
    (100, "Excelente"), (80, "Excelente"), (79, "Bueno"), (60, "Bueno"),
    (59, "Regular"), (40, "Regular"), (39, "Bajo"), (0, "Bajo"),
])
def test_evaluacion_principal(porcentaje, esperado):
    assert evaluacion_principal(porcentaje).etiqueta == esperado


@pytest.mark.parametrize("porcentaje, esperado", [
    (100, "Candidato recomendado"), (70, "Candidato recomendado"),
    (69, "Candidato con potencial"), (50, "Candidato con potencial"),
    (49, "Candidato no recomendado"), (0, "Candidato no recomendado"),
])
def test_recomendacion_final(porcentaje, esperado):
    assert recomendacion_final(porcentaje)[0].etiqueta == esperado


def test_ejemplo_del_readme_65_por_ciento():
    """65 % es «Bueno» en la evaluación principal y «con potencial» en la recomendación."""
    assert evaluacion_principal(65).etiqueta == "Bueno"
    assert recomendacion_final(65)[0].etiqueta == "Candidato con potencial"


@pytest.mark.parametrize("valor", [-1, 101, True, 50.5, "70"])
def test_porcentaje_invalido_en_criterios(valor):
    with pytest.raises(ValueError):
        evaluacion_principal(valor)
