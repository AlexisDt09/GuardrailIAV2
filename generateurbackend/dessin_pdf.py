# dessin_pdf.py

from fpdf import FPDF
from typing import List, Dict, Any, Optional
import json
import collections
import re
from datetime import datetime
import unicodedata
import math
from .utils import get_deduction_dimension, get_thickness_dimension


# --- PALETTE DE COULEURS ---
COLORS = {
    "poteau": (217, 30, 24), "lisse": (26, 188, 156), "barreau": (52, 152, 219),
    "cote": (142, 68, 173), "texte_noir": (0, 0, 0), "liaison": (108, 117, 125),
    "platine": (44, 62, 80),
    "cote_total": (192, 57, 43),   # Rouge pour la cote totale
    "cote_section": (39, 174, 96), # Vert pour la cote de section
    "cote_vide": (41, 128, 185)    # Bleu pour la cote de vide
}

# --- FONCTION DE NETTOYAGE DE TEXTE ---
def sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    nfkd_form = unicodedata.normalize('NFKD', text)
    latin_base = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return latin_base.encode('latin-1', 'ignore').decode('latin-1')

# --- CLASSE PDF PERSONNALISÉE ---
class PlanPDF(FPDF):
    def __init__(self, *args, **kwargs):
        self.titre_plan = sanitize_text(kwargs.pop('titre_plan', 'Plan de Fabrication'))
        super().__init__(*args, **kwargs)
        self.show_main_header = True

    def header(self):
        if self.show_main_header:
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, self.titre_plan, 0, 1, 'C')
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- FONCTION PRINCIPALE ---
def creer_plan_pdf(data: Dict[str, Any]):
    try:
        pdf = PlanPDF(orientation='L', unit='mm', format='A4', titre_plan=data.get('titre_plan', 'Sans Titre'))
        
        dessiner_page_1(pdf, data)
        
        pdf.show_main_header = False 

        grouped_morceaux = collections.defaultdict(list)
        for morceau in data['morceaux']:
            structure_key = json.dumps([(s.get('type'), s.get('longueur')) for s in morceau['structure']])
            group_key_with_angle = (morceau['angle'], structure_key)
            grouped_morceaux[group_key_with_angle].append(morceau)
            
        for group_key, morceaux_group in grouped_morceaux.items():
            dessiner_page_morceau(pdf, morceaux_group[0], data, len(morceaux_group))

        if data.get('platine_details'):
            dessiner_page_platine(pdf, data['platine_details'], data['poteau_dims'])
            
        sanitized_title = sanitize_text(data.get('titre_plan', 'plan')).replace(' ', '_').lower()
        filepath = f"{sanitized_title}.pdf"
        pdf.output(filepath)
        return filepath
    except Exception as e:
        print(f"Erreur lors de la création du PDF : {e}")
        import traceback
        traceback.print_exc()
        return None

# --- FONCTIONS DE DESSIN UTILITAIRES ---
def draw_horizontal_dim(pdf: FPDF, x, y, width, text):
    pdf.set_draw_color(*COLORS["cote"]); pdf.set_text_color(*COLORS["cote"]); pdf.set_line_width(0.2)
    pdf.line(x, y, x, y + 3); pdf.line(x + width, y, x + width, y + 3)
    pdf.line(x, y + 1.5, x + width, y + 1.5)
    
    pdf.set_font('Arial', '', 9)
    text_width = pdf.get_string_width(str(text))
    text_x = x + width / 2 - text_width / 2
    text_y = y + 2.5
    
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(text_x - 0.5, text_y, text_width + 1, 3.5, 'F')
    pdf.text(text_x, text_y + 3, str(text))

def draw_vertical_dim(pdf: FPDF, x, y, height, text, right_side=False):
    offset = -1 if not right_side else 1
    pdf.set_draw_color(*COLORS["cote"]); pdf.set_text_color(*COLORS["cote"]); pdf.set_line_width(0.2)
    pdf.line(x, y, x + 3 * offset, y); pdf.line(x, y - height, x + 3 * offset, y - height)
    pdf.line(x + 1.5 * offset, y, x + 1.5 * offset, y - height)

    pdf.set_font('Arial', '', 9); text_width = pdf.get_string_width(str(text))
    text_y = y - height / 2 + 1.5
    text_x = x - text_width - 2 if not right_side else x + 4

    pdf.set_fill_color(255, 255, 255)
    pdf.rect(text_x - 0.5, text_y - 1.5, text_width + 1, 3, 'F')
    pdf.text(text_x, text_y, str(text))

def draw_aligned_dim(pdf: FPDF, x1, y1, x2, y2, text, offset_dist, color=None):
    final_color = color if color else COLORS["cote"]
    pdf.set_draw_color(*final_color)
    pdf.set_text_color(*final_color)
    pdf.set_line_width(0.2)
    angle = math.atan2(y2 - y1, x2 - x1)
    
    offset_x = -offset_dist * math.sin(angle)
    offset_y = offset_dist * math.cos(angle)
    
    lx1, ly1 = x1 + offset_x, y1 + offset_y
    lx2, ly2 = x2 + offset_x, y2 + offset_y
    pdf.line(lx1, ly1, lx2, ly2)
    pdf.line(x1, y1, lx1, ly1); pdf.line(x2, y2, lx2, ly2)

    pdf.set_font('Arial', '', 9); text_width = pdf.get_string_width(text)
    mid_x, mid_y = (lx1 + lx2) / 2, (ly1 + ly2) / 2
    
    with pdf.rotation(math.degrees(angle), mid_x, mid_y):
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(mid_x - text_width / 2 - 1, mid_y - 2.5, text_width + 2, 3.5, 'F')
        pdf.text(mid_x - text_width / 2, mid_y, text)


def draw_annotation(pdf: FPDF, x, y, title, detail, color, align='L'):
    pdf.set_text_color(*color); title_safe = sanitize_text(title); detail_safe = f" ({sanitize_text(detail)})" if detail else ""
    if align == 'L':
        pdf.set_font('Arial', 'B', 9); title_width = pdf.get_string_width(title_safe)
        pdf.text(x, y, title_safe)
        pdf.set_font('Arial', 'I', 9); pdf.text(x + title_width, y, detail_safe)
    elif align == 'R':
        pdf.set_font('Arial', 'I', 9); detail_width = pdf.get_string_width(detail_safe)
        pdf.text(x - detail_width, y, detail_safe)
        pdf.set_font('Arial', 'B', 9); title_width = pdf.get_string_width(title_safe)
        pdf.text(x - detail_width - title_width, y, title_safe)

# --- DESSIN DES PAGES ---
def dessiner_vue_ensemble(pdf: FPDF, data: Dict[str, Any]):
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "3. Vue d'Ensemble", 0, 1, 'L')
    pdf.ln(5)

    morceaux = data['morceaux']
    if not morceaux: return

    # Calcul des points du chemin
    all_points = []
    x_cursor, y_cursor = 0, 0
    dims_map_visuel = {"poteau": get_deduction_dimension(data['poteau_dims']), "liaison": get_deduction_dimension(data['liaison_dims'])}

    for morceau in morceaux:
        angle_rad = math.radians(morceau['angle'])
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        structure_items = [item for item in morceau['structure'] if item.get('type') != 'rien']
        for item in structure_items:
            all_points.append((x_cursor, y_cursor))
            item_type = item['type']
            longueur = dims_map_visuel.get(item_type, item.get('longueur', 0))
            
            x_cursor += longueur * cos_a
            y_cursor += longueur * sin_a
    all_points.append((x_cursor, y_cursor))

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    
    bbox_width = max_x - min_x if max_x > min_x else 1
    
    drawing_area_width = pdf.w - 40
    scale = drawing_area_width / bbox_width if bbox_width > 0 else 1
    
    origin_x = 20 - min_x * scale
    origin_y = pdf.get_y() + 20 - min_y * scale
    
    pdf.set_draw_color(0,0,0)
    pdf.set_line_width(0.3)

    # Dessin des éléments
    x_cursor, y_cursor = 0, 0
    for morceau in morceaux:
        angle_rad = math.radians(morceau['angle'])
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        structure_items = [item for item in morceau['structure'] if item.get('type') != 'rien']

        for item in structure_items:
            item_type = item['type']
            start_x = x_cursor
            start_y = y_cursor
            
            longueur = dims_map_visuel.get(item_type, item.get('longueur', 0))
            
            x_cursor += longueur * cos_a
            y_cursor += longueur * sin_a
            
            p1 = (origin_x + start_x * scale, origin_y + start_y * scale)
            p2 = (origin_x + x_cursor * scale, origin_y + y_cursor * scale)

            thickness = 10 # Épaisseur visuelle
            dx = thickness * math.sin(angle_rad)
            dy = -thickness * math.cos(angle_rad)

            poly_points = [p1, p2, (p2[0] + dx, p2[1] + dy), (p1[0] + dx, p1[1] + dy)]
            
            if item_type in ['poteau', 'liaison']:
                pdf.set_fill_color(*COLORS[item_type])
                pdf.polygon(poly_points, style='F')
            else: # section
                pdf.set_fill_color(230, 230, 230)
                pdf.polygon(poly_points, style='DF')
                
                mid_x = (p1[0] + p2[0]) / 2
                mid_y = (p1[1] + p2[1]) / 2
                pdf.set_font('Arial', 'I', 8)
                text = f"L:{longueur:.0f} A:{morceau['angle']:.1f}°"
                pdf.text(mid_x - pdf.get_string_width(text)/2, mid_y - 4, text)
    pdf.ln(15)

def dessiner_page_1(pdf: FPDF, data: Dict[str, Any]):
    pdf.add_page()
    
    # 1. Cartouche
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. Informations Projet", 0, 1, 'L')
    client = data.get('nom_client', 'N/A')
    date_str = data.get('date_chantier', 'N/A')
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        formatted_date = date_str
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Client: {sanitize_text(client)}", 0, 1, 'L')
    pdf.cell(0, 6, f"Date Chantier: {formatted_date}", 0, 1, 'L')
    pdf.ln(10)

    # 2. Nomenclature
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. Nomenclature Globale", 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    col_widths = [60, 80, 40, 60]
    headers = ['Element', 'Details', 'Quantite', 'Longueur Unitaire']
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, sanitize_text(header), 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for item in data['nomenclature']:
        pdf.cell(col_widths[0], 6, sanitize_text(item['item']), 1)
        pdf.cell(col_widths[1], 6, sanitize_text(item['details']), 1)
        pdf.cell(col_widths[2], 6, str(item['quantite']), 1, 0, 'C')
        pdf.cell(col_widths[3], 6, f"{item['longueur_unitaire_mm']} mm", 1, 0, 'R')
        pdf.ln()
    pdf.ln(10)
    
    # 3. Vue d'ensemble
    dessiner_vue_ensemble(pdf, data)

def dessiner_page_morceau(pdf: FPDF, morceau: Dict[str, Any], all_data: Dict[str, Any], repetition: int):
    pdf.add_page()
    angle_deg = morceau['angle']
    titre = f"Detail du Morceau (Angle: {angle_deg}°)"
    if repetition > 1:
        titre += f" - (Quantite: {repetition})"
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 8, sanitize_text(titre), 0, 1, 'C')
    
    barreaux_info_parts = []
    if all_data['remplissage_type'] == 'barreaudage_vertical':
        for i, section in enumerate(morceau['sections_details']):
            if section['nombre_barreaux'] > 0:
                barreaux_info_parts.append(f"Section {i+1}: {section['nombre_barreaux']} barreaux, ecart {section['vide_entre_barreaux_mm']:.1f}mm")
    elif all_data['remplissage_type'] == 'barreaudage_horizontal' and all_data.get('remplissage_details'):
        details = all_data['remplissage_details']
        if details['nombre_barreaux'] > 0:
            barreaux_info_parts.append(f"{details['nombre_barreaux']} barreaux, ecart {details['vide_entre_barreaux_mm']:.1f}mm")

    if barreaux_info_parts:
        pdf.set_font('Arial', '', 9); pdf.set_text_color(*COLORS["texte_noir"])
        pdf.cell(0, 5, " | ".join(barreaux_info_parts), 0, 1, 'C')
    
    pdf.ln(5)

    angle_rad = math.radians(angle_deg)
    cos_angle, sin_angle = math.cos(angle_rad), math.sin(angle_rad)
    longueur_rampante_totale = morceau['longueur_totale']
    longueur_horizontale_totale = longueur_rampante_totale * cos_angle
    denivele_total = longueur_rampante_totale * sin_angle
    hauteur_totale = all_data['hauteur_totale']

    margin_x, margin_y_top, margin_y_bottom = 20, 40, 65
    drawing_width = pdf.w - 2 * margin_x
    drawing_height = pdf.h - margin_y_top - margin_y_bottom
    scale = min(drawing_width / longueur_horizontale_totale, drawing_height / (hauteur_totale + abs(denivele_total))) if longueur_horizontale_totale > 0 else 1
    
    origine_x = (pdf.w - longueur_horizontale_totale * scale) / 2
    origine_y = margin_y_top + (hauteur_totale + max(0, denivele_total)) * scale
    
    pdf.set_line_width(0.3)
    
    key_points = []
    x_cursor_horiz, y_cursor_vert = 0.0, 0.0
    
    structure_items = [item for item in morceau['structure'] if item.get('type') != 'rien']
    dims_map_visuel = {"poteau": get_deduction_dimension(all_data['poteau_dims']), "liaison": get_deduction_dimension(all_data['liaison_dims']), "barreau": get_deduction_dimension(all_data['barreau_dims'])}
    dims_map_epaisseur = {"lissehaute": get_thickness_dimension(all_data['lissehaute_dims']), "lissebasse": get_thickness_dimension(all_data['lissebasse_dims'])}
    
    section_details_iterator = iter(morceau['sections_details'])
    for item in structure_items:
        key_points.append({'x': x_cursor_horiz, 'y': y_cursor_vert, 'type': item['type']})
        item_type = item['type']
        ep_visuelle = dims_map_visuel.get(item_type, 0)
        
        if item_type in ['poteau', 'liaison']:
            pdf.set_draw_color(*COLORS[item_type])
            pdf.rect(origine_x + x_cursor_horiz * scale, origine_y - (y_cursor_vert + hauteur_totale) * scale, ep_visuelle * scale, hauteur_totale * scale, 'D')
            x_cursor_horiz += ep_visuelle
        elif item_type == 'section':
            section = next(section_details_iterator)
            longueur_rampante_libre = section['longueur_libre']
            longueur_horiz_libre = longueur_rampante_libre * cos_angle
            denivele_section = longueur_rampante_libre * sin_angle
            start_x, start_y = x_cursor_horiz, y_cursor_vert
            end_x, end_y = start_x + longueur_horiz_libre, start_y + denivele_section
            lisse_haute_ep, lisse_basse_ep = dims_map_epaisseur['lissehaute'], dims_map_epaisseur['lissebasse']
            pdf.set_draw_color(*COLORS["lisse"])
            lh_p1 = (origine_x + start_x * scale, origine_y - (start_y + hauteur_totale) * scale); lh_p2 = (origine_x + end_x * scale, origine_y - (end_y + hauteur_totale) * scale); lh_p3 = (origine_x + end_x * scale, origine_y - (end_y + hauteur_totale - lisse_haute_ep) * scale); lh_p4 = (origine_x + start_x * scale, origine_y - (start_y + hauteur_totale - lisse_haute_ep) * scale)
            pdf.polygon([lh_p1, lh_p2, lh_p3, lh_p4], style='D')
            lb_p1 = (origine_x + start_x * scale, origine_y - (start_y + all_data['hauteur_lisse_basse'] + lisse_basse_ep) * scale); lb_p2 = (origine_x + end_x * scale, origine_y - (end_y + all_data['hauteur_lisse_basse'] + lisse_basse_ep) * scale); lb_p3 = (origine_x + end_x * scale, origine_y - (end_y + all_data['hauteur_lisse_basse']) * scale); lb_p4 = (origine_x + start_x * scale, origine_y - (start_y + all_data['hauteur_lisse_basse']) * scale)
            pdf.polygon([lb_p1, lb_p2, lb_p3, lb_p4], style='D')
            
            if all_data['remplissage_type'] == 'barreaudage_vertical' and section['nombre_barreaux'] > 0:
                pdf.set_draw_color(*COLORS["barreau"])
                barreau_ep_visuel = dims_map_visuel.get('barreau', 0)
                hauteur_barreau = hauteur_totale - all_data['hauteur_lisse_basse'] - lisse_haute_ep - lisse_basse_ep
                for k in range(section['nombre_barreaux']):
                    pos_rampe = section['jeu_depart_mm'] + k * (section['vide_entre_barreaux_mm'] + get_deduction_dimension(all_data['barreau_dims']))
                    pos_horiz, pos_vert_denivele = pos_rampe * cos_angle, pos_rampe * sin_angle
                    x_barreau = origine_x + (start_x + pos_horiz) * scale
                    y_barreau_top = origine_y - (start_y + pos_vert_denivele + all_data['hauteur_lisse_basse'] + lisse_basse_ep + hauteur_barreau) * scale
                    pdf.rect(x_barreau, y_barreau_top, barreau_ep_visuel * scale, hauteur_barreau * scale, 'D')
            
            elif all_data['remplissage_type'] == 'barreaudage_horizontal' and all_data.get('remplissage_details'):
                details = all_data['remplissage_details']
                if details['nombre_barreaux'] > 0:
                    pdf.set_draw_color(*COLORS["barreau"])
                    barreau_ep_visuel = get_thickness_dimension(all_data['barreau_dims'])
                    for k in range(details['nombre_barreaux']):
                        y_pos = details['jeu_depart_mm'] + k * (details['vide_entre_barreaux_mm'] + barreau_ep_visuel)
                        p1 = (origine_x + start_x * scale, origine_y - (start_y + all_data['hauteur_lisse_basse'] + lisse_basse_ep + y_pos) * scale)
                        p2 = (origine_x + end_x * scale, origine_y - (end_y + all_data['hauteur_lisse_basse'] + lisse_basse_ep + y_pos) * scale)
                        pdf.line(p1[0], p1[1], p2[0], p2[1])

            x_cursor_horiz, y_cursor_vert = end_x, end_y
    key_points.append({'x': x_cursor_horiz, 'y': y_cursor_vert, 'type': 'fin'})

    draw_vertical_dim(pdf, origine_x - 5, origine_y - (denivele_total if denivele_total < 0 else 0) * scale, hauteur_totale * scale, str(hauteur_totale))
    draw_vertical_dim(pdf, origine_x - 15, origine_y, all_data['hauteur_lisse_basse'] * scale, str(all_data['hauteur_lisse_basse']))
    
    p1_total_x = origine_x + key_points[0]['x'] * scale; p1_total_y = origine_y - key_points[0]['y'] * scale
    p2_total_x = origine_x + key_points[-1]['x'] * scale; p2_total_y = origine_y - key_points[-1]['y'] * scale
    draw_aligned_dim(pdf, p1_total_x, p1_total_y, p2_total_x, p2_total_y, f"L. Totale: {longueur_rampante_totale:.0f}", 35, color=COLORS["cote_total"])

    section_details_iterator_dim = iter(morceau['sections_details'])
    for i in range(len(structure_items)):
        if structure_items[i]['type'] == 'section':
            section = next(section_details_iterator_dim)
            
            elem_gauche = structure_items[i-1]
            elem_droit = structure_items[i+1]
            
            is_gauche_extremite = (i-1 == 0)
            is_droit_extremite = (i+1 == len(structure_items) - 1)
            
            ep_gauche = dims_map_visuel.get(elem_gauche['type'], 0)
            ep_droit = dims_map_visuel.get(elem_droit['type'], 0)
            
            pt_gauche = key_points[i-1]
            pt_droit = key_points[i+1]
            
            offset_gauche = 0 if is_gauche_extremite else ep_gauche / 2
            offset_droit = ep_droit if is_droit_extremite else ep_droit / 2
            
            p1_sec_x_virtuel = pt_gauche['x'] + offset_gauche
            p1_sec_y_virtuel = pt_gauche['y'] + offset_gauche * sin_angle
            
            p2_sec_x_virtuel = pt_droit['x'] + offset_droit
            p2_sec_y_virtuel = pt_droit['y'] + offset_droit * sin_angle
            
            p1_sec_x = origine_x + p1_sec_x_virtuel * scale
            p1_sec_y = origine_y - p1_sec_y_virtuel * scale
            p2_sec_x = origine_x + p2_sec_x_virtuel * scale
            p2_sec_y = origine_y - p2_sec_y_virtuel * scale
            draw_aligned_dim(pdf, p1_sec_x, p1_sec_y, p2_sec_x, p2_sec_y, f"Section: {section['longueur_section']:.0f}", 15, color=COLORS["cote_section"])

            pt_debut_vide = key_points[i]
            p1_vide_x = origine_x + pt_debut_vide['x'] * scale
            p1_vide_y = origine_y - pt_debut_vide['y'] * scale
            p2_vide_x = origine_x + pt_droit['x'] * scale
            p2_vide_y = origine_y - pt_droit['y'] * scale
            draw_aligned_dim(pdf, p1_vide_x, p1_vide_y, p2_vide_x, p2_vide_y, f"Vide: {section['longueur_libre']:.0f}", 25, color=COLORS["cote_vide"])
            
    draw_annotation(pdf, 20, 20, "Poteau:", all_data['poteau_dims'], COLORS["poteau"], align='L')
    draw_annotation(pdf, 20, 25, "Liaison:", all_data['liaison_dims'], COLORS["liaison"], align='L')
    draw_annotation(pdf, 20, 30, "Barreau:", all_data['barreau_dims'], COLORS["barreau"], align='L')
    draw_annotation(pdf, pdf.w - 20, 20, "Lisse Haute:", all_data['lissehaute_dims'], COLORS["lisse"], align='R')
    draw_annotation(pdf, pdf.w - 20, 25, "Lisse Basse:", all_data['lissebasse_dims'], COLORS["lisse"], align='R')

def dessiner_page_platine(pdf: FPDF, platine: Dict[str, Any], poteau_dims: str):
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, 'Detail de la Platine de Fixation', 0, 1, 'L'); pdf.ln(10)
    pdf.set_font('Arial', 'BU', 10); pdf.cell(0, 10, 'Vue de dessus', 0, 1, 'C'); pdf.ln(5)
    p_l, p_w = platine['longueur'], platine['largeur']; center_x, center_y = pdf.w / 2, 80
    pdf.set_draw_color(*COLORS['platine']); pdf.set_line_width(0.5); pdf.rect(center_x - p_l / 2, center_y - p_w / 2, p_l, p_w)
    po_l, po_w = get_thickness_dimension(poteau_dims), get_deduction_dimension(poteau_dims)
    pdf.set_draw_color(*COLORS['poteau']); pdf.set_line_width(0.3); pdf.rect(center_x - po_l / 2, center_y - po_w / 2, po_l, po_w)
    e_l, e_w, trou_d = platine['entraxe_longueur'], platine['entraxe_largeur'], platine['diametre_trous']
    pdf.set_draw_color(0,0,0); pdf.set_line_width(0.2)
    coords = [(center_x - e_l / 2, center_y - e_w / 2), (center_x + e_l / 2, center_y - e_w / 2), (center_x - e_l / 2, center_y + e_w / 2), (center_x + e_l / 2, center_y + e_w / 2)]
    for x, y in coords: pdf.circle(x, y, trou_d / 2)
    draw_horizontal_dim(pdf, center_x - p_l / 2, center_y + p_w / 2 + 10, p_l, str(p_l))
    draw_horizontal_dim(pdf, center_x - e_l / 2, center_y + p_w / 2 + 20, e_l, f"Entraxe {e_l}")
    draw_vertical_dim(pdf, center_x - p_l / 2 - 10, center_y + p_w / 2, p_w, str(p_w))
    draw_vertical_dim(pdf, center_x - p_l / 2 - 20, center_y + e_w / 2, e_w, f"Entraxe {e_w}")
    pdf.set_y(pdf.h - 60); pdf.set_font('Arial', 'BU', 10); pdf.cell(0, 10, 'Vue de cote', 0, 1, 'C'); pdf.ln(5)
    p_e = platine['epaisseur']
    pdf.set_draw_color(*COLORS['platine']); pdf.set_line_width(0.5); pdf.rect(center_x - p_l / 2, pdf.h - 40, p_l, p_e)
    draw_vertical_dim(pdf, center_x + p_l / 2 + 5, pdf.h - 40 + p_e, p_e, str(p_e), right_side=True)

