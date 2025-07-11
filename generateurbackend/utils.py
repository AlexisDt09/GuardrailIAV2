# utils.py

import re

def get_deduction_dimension(dim_string: str) -> float:
    """
    Extrait la deuxième dimension (souvent la 'profondeur' ou 'largeur de déduction') d'une chaîne de caractères.
    Ex: "40x40" -> 40, "Plat 50x8" -> 8
    """
    if not dim_string:
        return 0
    # Trouve tous les nombres (entiers ou décimaux)
    numbers = re.findall(r'(\d+\.?\d*)', dim_string)
    # S'il y a au moins deux nombres, on prend le deuxième
    if len(numbers) >= 2:
        return float(numbers[1])
    # S'il n'y en a qu'un, on le prend par défaut
    elif len(numbers) == 1:
        return float(numbers[0])
    return 0

def get_thickness_dimension(dim_string: str) -> float:
    """
    Extrait la première dimension (souvent l'épaisseur) d'une chaîne de caractères.
    Ex: "40x40x3" -> 40, "Ø42.4x2" -> 42.4
    """
    if not dim_string:
        return 0
    # Trouve tous les nombres (entiers ou décimaux)
    numbers = re.findall(r'(\d+\.?\d*)', dim_string)
    # On prend le premier nombre trouvé
    if len(numbers) > 0:
        return float(numbers[0])
    return 0
