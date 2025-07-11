# test_main.py
import pytest
# On suppose que le fichier main.py est dans le même dossier ou dans le PYTHONPATH
from main import get_deduction_dimension, get_thickness_dimension, calculate_repartition, RepartitionResult

# --- Tests pour get_deduction_dimension ---

def test_get_deduction_dimension_double():
    """Teste l'extraction de la 2ème dimension pour un profilé rectangulaire."""
    assert get_deduction_dimension("40x20") == 20

def test_get_deduction_dimension_square():
    """Teste avec un profilé carré."""
    assert get_deduction_dimension("40x40") == 40

def test_get_deduction_dimension_single():
    """Teste avec une seule dimension (rond, carré)."""
    assert get_deduction_dimension("40") == 40

def test_get_deduction_dimension_with_thickness():
    """Teste un format complexe comme 50x8x2, doit retourner 8."""
    assert get_deduction_dimension("50x8x2") == 8

def test_get_deduction_dimension_empty():
    """Teste avec une chaîne vide."""
    assert get_deduction_dimension("") == 0

def test_get_deduction_dimension_invalid():
    """Teste avec une chaîne invalide."""
    assert get_deduction_dimension("abc") == 0

# --- Tests pour get_thickness_dimension ---

def test_get_thickness_dimension_double():
    """Teste l'extraction de la 1ère dimension."""
    assert get_thickness_dimension("40x20") == 40

def test_get_thickness_dimension_square():
    """Teste avec un profilé carré."""
    assert get_thickness_dimension("40x40") == 40

def test_get_thickness_dimension_single():
    """Teste avec une seule dimension."""
    assert get_thickness_dimension("40") == 40

def test_get_thickness_dimension_empty():
    """Teste avec une chaîne vide."""
    assert get_thickness_dimension("") == 0

def test_get_thickness_dimension_invalid():
    """Teste avec une chaîne invalide."""
    assert get_thickness_dimension("abc") == 0

# --- Tests pour calculate_repartition ---

def test_calculate_repartition_normal():
    """Teste un cas de répartition standard."""
    # Avec une longueur de 940, on doit obtenir 7 barreaux espacés de 100mm.
    result = calculate_repartition(longueur_libre=940, epaisseur_barreau=20, ecart_maximal=110)
    assert result.nombre_barreaux == 7
    assert result.vide_entre_barreaux_mm == pytest.approx(100)
    assert result.jeu_depart_mm == pytest.approx(100)

def test_calculate_repartition_zero_length():
    """Teste avec une longueur libre nulle."""
    result = calculate_repartition(longueur_libre=0, epaisseur_barreau=20, ecart_maximal=110)
    assert result.nombre_barreaux == 0
    assert result.jeu_depart_mm == 0

def test_calculate_repartition_negative_length():
    """Teste avec une longueur libre négative."""
    result = calculate_repartition(longueur_libre=-100, epaisseur_barreau=20, ecart_maximal=110)
    assert result.nombre_barreaux == 0
    assert result.jeu_depart_mm == -100

def test_calculate_repartition_one_barreau():
    """Teste un cas où un seul barreau doit être placé."""
    # Avec une longueur de 200, on doit obtenir 1 barreau.
    # Espacement = (200 - 20) / (1 + 1) = 90
    result = calculate_repartition(longueur_libre=200, epaisseur_barreau=20, ecart_maximal=110)
    assert result.nombre_barreaux == 1
    assert result.vide_entre_barreaux_mm == pytest.approx(90)
    assert result.jeu_depart_mm == pytest.approx(90)
    
def test_calculate_repartition_no_barreau_possible():
    """Teste un cas où aucun barreau ne peut tenir."""
    result = calculate_repartition(longueur_libre=100, epaisseur_barreau=20, ecart_maximal=110)
    assert result.nombre_barreaux == 0
    assert result.jeu_depart_mm == 100

def test_calculate_repartition_exact_fit():
    """Teste un cas où les espacements tombent juste sur l'écart maximal."""
    # 3 barreaux de 20mm + 4 espacements de 100mm = 460mm
    result = calculate_repartition(longueur_libre=460, epaisseur_barreau=20, ecart_maximal=100)
    assert result.nombre_barreaux == 3
    assert result.vide_entre_barreaux_mm == pytest.approx(100)
    assert result.jeu_depart_mm == pytest.approx(100)
