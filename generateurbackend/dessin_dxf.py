# dessin_dxf.py

from typing import Dict, Any, Optional
import ezdxf
from ezdxf.document import Drawing
from ezdxf.math import Vec2, BoundingBox
from ezdxf.enums import TextEntityAlignment
from ezdxf import bbox
from datetime import datetime
import math

# Importations des fonctions utilitaires pour obtenir les dimensions des profilés
from utils import get_deduction_dimension, get_thickness_dimension

# Dictionnaire des couleurs ACI (AutoCAD Color Index) pour les calques
LAYER_COLORS = {
    "POTEAU": 1,      # Rouge
    "LIAISON": 8,     # Gris
    "LISSE": 3,       # Vert
    "BARREAU": 5,     # Bleu
    "PLATINE": 4,     # Cyan
    "COTES": 6,       # Magenta
    "TEXTE": 7,       # Blanc/Noir (couleur par défaut)
    "REFERENCE": 9,   # Gris clair pour les lignes de construction
    "CARTOUCHE": 7,   # Blanc/Noir pour le cartouche
    "COTES_SECTION": 11, # Cyan clair
    "COTES_VIDE": 151,   # Vert-Bleu
    "COTES_TOTAL": 1,    # Rouge, pour la visibilité
}

# --- FONCTIONS UTILITAIRES DE DESSIN ---

def add_annotation(msp, text: str, position: Vec2, height=25, layer="TEXTE", align: TextEntityAlignment = TextEntityAlignment.TOP_LEFT):
    """Ajoute une annotation texte au plan avec un alignement spécifié."""
    msp.add_text(
        text,
        dxfattribs={"layer": layer, "height": height}
    ).set_placement(position, align=align)

def add_aligned_dim_with_mask(msp, p1: Vec2, p2: Vec2, distance: float, text: str, dim_style: str, layer="COTES"):
    """Ajoute une cote alignée avec un masque d'arrière-plan."""
    dim = msp.add_aligned_dim(p1=p1, p2=p2, distance=distance, text=text, dimstyle=dim_style, dxfattribs={"layer": layer})
    dim.render()

# --- FONCTIONS DE DESSIN PRINCIPALES ---

def draw_legend(msp, data: Dict[str, Any], origin: Vec2, text_height=60):
    """Dessine une légende avec les dimensions des profilés."""
    add_annotation(msp, "LEGENDE", origin, height=text_height*1.2, layer="TEXTE")
    
    y_offset = -text_height * 2
    
    legend_items = [
        ("Poteau:", data['poteau_dims'], "POTEAU"),
        ("Liaison:", data['liaison_dims'], "LIAISON"),
        ("Lisse Haute:", data['lissehaute_dims'], "LISSE"),
        ("Lisse Basse:", data['lissebasse_dims'], "LISSE"),
        ("Barreau:", data['barreau_dims'], "BARREAU"),
    ]
    
    for label, dim, layer in legend_items:
        add_annotation(msp, f"{label} {dim}", origin + (0, y_offset), height=text_height, layer=layer)
        y_offset -= text_height * 1.5


def draw_cartouche(msp, data: Dict[str, Any], origin: Vec2, width=5000, height=1800, text_height=80):
    """Dessine un cartouche d'informations pour le plan."""
    layer = "CARTOUCHE"
    msp.add_lwpolyline([origin, origin + (width, 0), origin + (width, height), origin + (0, height)], close=True, dxfattribs={"layer": layer})
    
    line_y_1 = origin + (0, height * 2/3)
    msp.add_line(line_y_1, line_y_1 + (width, 0), dxfattribs={"layer": layer})
    line_y_2 = origin + (0, height * 1/3)
    msp.add_line(line_y_2, line_y_2 + (width, 0), dxfattribs={"layer": layer})

    margin = text_height / 2
    
    titre_pos = origin + (margin, height * 2/3 + margin * 1.5)
    add_annotation(msp, f"Titre: {data.get('titre_plan', 'N/A')}", titre_pos, height=text_height, layer=layer)
    
    client_pos = origin + (margin, height * 1/3 + margin * 1.5)
    add_annotation(msp, f"Client: {data.get('nom_client', 'N/A')}", client_pos, height=text_height, layer=layer)
    
    try:
        date_obj = datetime.strptime(data.get('date_chantier', ''), '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        formatted_date = data.get('date_chantier', 'N/A')
    date_pos = origin + (margin, margin * 1.5)
    add_annotation(msp, f"Date: {formatted_date}", date_pos, height=text_height, layer=layer)

def draw_vue_ensemble_dxf(msp, data: Dict[str, Any], origin: Vec2, dim_style: str):
    """Dessine une vue d'ensemble schématique de tous les morceaux."""
    add_annotation(msp, "VUE D'ENSEMBLE", origin, height=100, layer="TEXTE")
    
    cursor = origin + (0, -500)
    dims_map_visuel = {"poteau": get_deduction_dimension(data['poteau_dims']), "liaison": get_deduction_dimension(data['liaison_dims'])}
    
    for morceau in data['morceaux']:
        angle_rad = math.radians(morceau['angle'])
        structure_items = [item for item in morceau['structure'] if item.get('type') != 'rien']

        for item in structure_items:
            item_type = item['type']
            start_point = cursor
            
            longueur = dims_map_visuel.get(item_type, item.get('longueur', 0))
            
            end_point = start_point + Vec2.from_angle(angle_rad, longueur)

            thickness = 250
            v_thickness = Vec2.from_angle(angle_rad + math.pi / 2, thickness)
            
            p1 = start_point
            p2 = end_point
            p3 = end_point + v_thickness
            p4 = start_point + v_thickness
            
            poly_points = [p1, p2, p3, p4]
            
            # MODIF: Utiliser le calque approprié pour le contour et supprimer le remplissage
            layer_name = "REFERENCE"
            if item_type in ['poteau', 'liaison']:
                layer_name = item_type.upper()

            msp.add_lwpolyline(poly_points, close=True, dxfattribs={"layer": layer_name})
            
            if item_type == 'section':
                mid_point = p1.lerp(p2)
                annot_pos = mid_point + v_thickness.normalize() * (thickness + 50)
                add_annotation(msp, f"L:{longueur:.0f} A:{morceau['angle']:.1f}°", annot_pos, height=50, layer="TEXTE", align=TextEntityAlignment.BOTTOM_CENTER)

            cursor = end_point

def draw_morceau_view(msp, morceau: Dict[str, Any], all_data: Dict[str, Any], origin: Vec2, dim_style: str):
    """Dessine la vue détaillée d'un morceau, incluant la géométrie et toutes les cotes."""
    hauteur_totale = all_data['hauteur_totale']
    hauteur_lisse_basse = all_data['hauteur_lisse_basse']
    angle_deg = morceau.get('angle', 0)
    angle_rad = math.radians(angle_deg)
    cos_angle, sin_angle = math.cos(angle_rad), math.sin(angle_rad)
    longueur_rampante_totale = morceau.get('longueur_totale', 0)

    # --- 1. DESSIN DE LA GÉOMÉTRIE ---
    x_cursor_horiz, y_cursor_vert = origin.x, origin.y
    key_points = []
    structure_items = [item for item in morceau['structure'] if item.get('type') != 'rien']
    dims_map_visuel = {"poteau": get_deduction_dimension(all_data['poteau_dims']), "liaison": get_deduction_dimension(all_data['liaison_dims'])}
    
    section_details_iterator = iter(morceau['sections_details'])
    for item in structure_items:
        key_points.append({'x': x_cursor_horiz, 'y': y_cursor_vert, 'type': item['type']})
        item_type = item['type']
        ep_visuelle = dims_map_visuel.get(item_type, 0)
        
        if item_type in ['poteau', 'liaison']:
            p1 = Vec2(x_cursor_horiz, y_cursor_vert)
            p2 = Vec2(x_cursor_horiz, y_cursor_vert + hauteur_totale)
            msp.add_lwpolyline([p1, p1 + (ep_visuelle, 0), p2 + (ep_visuelle, 0), p2], close=True, dxfattribs={"layer": item_type.upper()})
            x_cursor_horiz += ep_visuelle
        elif item_type == 'section':
            section = next(section_details_iterator)
            longueur_rampante_libre = section['longueur_libre']
            longueur_horiz_libre = longueur_rampante_libre * cos_angle
            denivele_section = longueur_rampante_libre * sin_angle
            
            start_x, start_y = x_cursor_horiz, y_cursor_vert
            end_x, end_y = start_x + longueur_horiz_libre, start_y + denivele_section
            
            lisse_haute_ep = get_thickness_dimension(all_data['lissehaute_dims'])
            lisse_basse_ep = get_thickness_dimension(all_data['lissebasse_dims'])
            
            # Lisses
            lh_p1 = Vec2(start_x, start_y + hauteur_totale - lisse_haute_ep); lh_p2 = Vec2(end_x, end_y + hauteur_totale - lisse_haute_ep); lh_p3 = Vec2(end_x, end_y + hauteur_totale); lh_p4 = Vec2(start_x, start_y + hauteur_totale)
            msp.add_lwpolyline([lh_p1, lh_p2, lh_p3, lh_p4], close=True, dxfattribs={"layer": "LISSE"})
            lb_p1 = Vec2(start_x, start_y + hauteur_lisse_basse); lb_p2 = Vec2(end_x, end_y + hauteur_lisse_basse); lb_p3 = Vec2(end_x, end_y + hauteur_lisse_basse + lisse_basse_ep); lb_p4 = Vec2(start_x, start_y + hauteur_lisse_basse + lisse_basse_ep)
            msp.add_lwpolyline([lb_p1, lb_p2, lb_p3, lb_p4], close=True, dxfattribs={"layer": "LISSE"})

            # Barreaux
            if section.get('nombre_barreaux', 0) > 0:
                barreau_ep = get_deduction_dimension(all_data['barreau_dims'])
                hauteur_barreau = hauteur_totale - hauteur_lisse_basse - lisse_haute_ep - lisse_basse_ep
                espacement_rampe = section.get('vide_entre_barreaux_mm', 0)
                jeu_depart_rampe = section.get('jeu_depart_mm', 0)

                for j in range(section['nombre_barreaux']):
                    pos_x_rampe = jeu_depart_rampe + j * (barreau_ep + espacement_rampe)
                    pos_x_horiz = start_x + pos_x_rampe * cos_angle
                    pos_y_denivele = pos_x_rampe * sin_angle
                    barreau_y_start = start_y + hauteur_lisse_basse + lisse_basse_ep + pos_y_denivele
                    barreau_p1 = Vec2(pos_x_horiz, barreau_y_start)
                    msp.add_lwpolyline([barreau_p1, barreau_p1 + (barreau_ep, 0), barreau_p1 + (barreau_ep, hauteur_barreau), barreau_p1 + (0, hauteur_barreau)], close=True, dxfattribs={"layer": "BARREAU"})
            
            # Annotation pour le barreaudage
            annot_text = f"{section['nombre_barreaux']} barreaux / Ecart: {section['vide_entre_barreaux_mm']:.1f}mm"
            annot_pos = Vec2(start_x + longueur_horiz_libre / 2, start_y + denivele_section / 2 + hauteur_totale + 100)
            add_annotation(msp, annot_text, annot_pos, height=50, layer="TEXTE", align=TextEntityAlignment.BOTTOM_CENTER)

            x_cursor_horiz, y_cursor_vert = end_x, end_y
    
    key_points.append({'x': x_cursor_horiz, 'y': y_cursor_vert, 'type': 'fin'})

    # --- 2. DESSIN DES COTES ---
    p1_h = Vec2(origin.x, origin.y); p2_h = Vec2(origin.x, origin.y + hauteur_totale)
    msp.add_linear_dim(base=p1_h + (-150, hauteur_totale / 2), p1=p1_h, p2=p2_h, angle=90, text=f"{hauteur_totale}", dimstyle=dim_style, dxfattribs={"layer": "COTES"}).render()

    p2_hsl = Vec2(origin.x, origin.y + hauteur_lisse_basse)
    msp.add_linear_dim(base=p1_h + (-250, hauteur_lisse_basse / 2), p1=p1_h, p2=p2_hsl, angle=90, text=f"{hauteur_lisse_basse}", dimstyle=dim_style, dxfattribs={"layer": "COTES"}).render()

    p1_total = Vec2(key_points[0]['x'], key_points[0]['y'])
    p2_total = Vec2(key_points[-1]['x'], key_points[-1]['y'])
    add_aligned_dim_with_mask(msp, p1_total, p2_total, -350, f"Longueur Totale: {longueur_rampante_totale:.0f}", dim_style, layer="COTES_TOTAL")

    section_details_iterator_dim = iter(morceau['sections_details'])
    for i in range(len(structure_items)):
        if structure_items[i]['type'] == 'section':
            section = next(section_details_iterator_dim)
            elem_gauche = structure_items[i-1]; elem_droit = structure_items[i+1]
            is_gauche_extremite = (i-1 == 0); is_droit_extremite = (i+1 == len(structure_items) - 1)
            ep_gauche = dims_map_visuel.get(elem_gauche['type'], 0); ep_droit = dims_map_visuel.get(elem_droit['type'], 0)
            
            pt_gauche_sec = key_points[i-1]; offset_gauche = 0 if is_gauche_extremite else ep_gauche / 2
            p1_sec = Vec2(pt_gauche_sec['x'] + offset_gauche, pt_gauche_sec['y'] + offset_gauche * sin_angle)
            pt_droit_sec = key_points[i+1]; offset_droit = ep_droit if is_droit_extremite else ep_droit / 2
            p2_sec = Vec2(pt_droit_sec['x'] + offset_droit, pt_droit_sec['y'] + offset_droit * sin_angle)
            add_aligned_dim_with_mask(msp, p1_sec, p2_sec, -150, f"{section['longueur_section']:.0f}", dim_style, layer="COTES_SECTION")

            pt_debut_vide = key_points[i]
            p1_vide = Vec2(pt_debut_vide['x'], pt_debut_vide['y']); p2_vide = Vec2(key_points[i+1]['x'], key_points[i+1]['y'])
            add_aligned_dim_with_mask(msp, p1_vide, p2_vide, -250, f"Vide: {section['longueur_libre']:.0f}", dim_style, layer="COTES_VIDE")

def creer_plan_dxf(data: Dict[str, Any]) -> Optional[Drawing]:
    """Génère un plan de garde-corps complet au format DXF, propre et organisé."""
    doc: Drawing = ezdxf.new(dxfversion='AC1027')
    msp = doc.modelspace()

    for name, color_index in LAYER_COLORS.items():
        doc.layers.add(name=name, color=color_index)

    dim_style_name = "METALLERIE_MASQUE"
    doc.dimstyles.new(
        name=dim_style_name,
        dxfattribs={
            "dimtxt": 40, "dimasz": 15, "dimblk": "ARCHTICK",
            "dimtfill": 1, "dimtfillclr": 256
        },
    )

    # Positionnement en haut à gauche pour le cartouche et la légende
    cartouche_origin = Vec2(0, 0)
    draw_cartouche(msp, data, cartouche_origin)
    
    legend_origin = cartouche_origin + (5500, 0) # À droite du cartouche
    draw_legend(msp, data, legend_origin)
    
    # Positionnement de la vue d'ensemble en dessous
    vue_ensemble_origin = cartouche_origin + (0, -2500)
    draw_vue_ensemble_dxf(msp, data, vue_ensemble_origin, dim_style_name)

    # Positionnement des vues détaillées
    detail_origin = vue_ensemble_origin + (0, -3000) # Encore plus bas
    cursor = detail_origin
    
    for m in data['morceaux']:
        draw_morceau_view(msp, m, data, cursor, dim_style_name)
        longueur_horizontale_totale = m.get('longueur_totale', 0) * math.cos(math.radians(m.get('angle', 0)))
        cursor += (longueur_horizontale_totale + 1500, 0)
    
    try:
        final_extents = bbox.extents(msp)
        if final_extents.has_data:
            doc.header['$EXTMIN'] = tuple(final_extents.extmin)
            doc.header['$EXTMAX'] = tuple(final_extents.extmax)
    except Exception as e:
        print(f"Avertissement : Impossible de calculer les limites du dessin. Erreur: {e}")

    return doc
