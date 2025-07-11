# ===============================================
# 1. SECTION DES IMPORTS
# ===============================================
import os
import json
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re
import math
from pathlib import Path
import subprocess
import tempfile
import time
import shutil

try:
    import google.generativeai as genai
    from PIL import Image
    import io
except ImportError:
    genai = None
    Image = None
    io = None

from .dessin_pdf import creer_plan_pdf
from .dessin_dxf import creer_plan_dxf
from .utils import get_deduction_dimension, get_thickness_dimension

# ===============================================
# 2. CONFIGURATION INITIALE ET CHARGEMENT DES VARIABLES
# ===============================================
load_dotenv()

app = FastAPI(title="API Garde-Corps v25 (Phase 1)", version="25.0.0")

# Le chemin du convertisseur DWG est spécifique à Windows.
# Il est mis en commentaire pour que le déploiement sur Render (Linux) fonctionne.
# ODA_CONVERTER_PATH = r"C:\Program Files\ODA\ODAFileConverter 26.4.0\ODAFileConverter.exe"

# Monte d'un niveau pour pointer vers la racine du projet (le dossier qui contient 'frontend' et 'generateurbackend')
BASE_DIR = Path(__file__).resolve().parent.parent

# ===============================================
# 3. MODÈLES DE DONNÉES (PYDANTIC)
# ===============================================
class StructureItem(BaseModel):
    type: str
    longueur: Optional[float] = None

class MorceauData(BaseModel):
    nombre_sections: int
    structure: List[StructureItem]
    angle: Optional[float] = 0.0

class PlatineDetails(BaseModel):
    longueur: float
    largeur: float
    epaisseur: float
    nombre_trous: int
    diametre_trous: float
    entraxe_longueur: float
    entraxe_largeur: float

class ProjectData(BaseModel):
    titre_plan: str
    nom_client: str
    date_chantier: str
    hauteur_totale: int
    hauteur_lisse_basse: int
    poteau_dims: str
    liaison_dims: str
    lissehaute_dims: str
    lissebasse_dims: str
    barreau_dims: str
    ecart_barreaux: int
    type_fixation: str
    remplissage_type: str
    platine_dimensions: Optional[str] = None
    platine_trous: Optional[str] = None
    platine_entraxes: Optional[str] = None
    nombre_morceaux: int
    morceaux_identiques: str
    morceaux: List[MorceauData]

class NomenclatureItem(BaseModel):
    item: str
    details: str
    quantite: int
    longueur_unitaire_mm: int

class SectionPlan(BaseModel):
    longueur_section: float
    longueur_libre: float
    nombre_barreaux: int
    vide_entre_barreaux_mm: float
    jeu_depart_mm: float

class MorceauPlan(BaseModel):
    id: int
    longueur_totale: float
    angle: float
    structure: List[StructureItem]
    sections_details: List[SectionPlan]

class RepartitionResult(BaseModel):
    nombre_barreaux: int
    vide_entre_barreaux_mm: float
    jeu_depart_mm: float

class FinalPlanData(BaseModel):
    titre_plan: str
    nom_client: str
    date_chantier: str
    description_projet: str
    nomenclature: List[NomenclatureItem]
    morceaux: List[MorceauPlan]
    hauteur_totale: int
    hauteur_lisse_basse: int
    poteau_dims: str
    liaison_dims: str
    lissehaute_dims: str
    lissebasse_dims: str
    barreau_dims: str
    platine_details: Optional[PlatineDetails] = None
    remplissage_type: str
    remplissage_details: Optional[RepartitionResult] = None

class DescriptionData(BaseModel):
    description: str

class SchemaData(BaseModel):
    image_data: str

class ParsedFormData(BaseModel):
    titre_plan: Optional[str] = None
    nom_client: Optional[str] = None
    date_chantier: Optional[str] = None
    nombre_morceaux: Optional[int] = None
    morceaux_identiques: Optional[str] = "non"
    hauteur_totale: Optional[int] = 1020
    hauteur_lisse_basse: Optional[int] = 100
    poteau_dims: Optional[str] = "40x40"
    liaison_dims: Optional[str] = "40x20"
    lissehaute_dims: Optional[str] = "40x40"
    lissebasse_dims: Optional[str] = "40x40"
    barreau_dims: Optional[str] = "20x20"
    ecart_barreaux: Optional[int] = 110
    morceaux: Optional[List[MorceauData]] = []


# ===============================================
# 4. MIDDLEWARE ET GESTION DES ERREURS
# ===============================================

# Drapeau global pour suivre l'état de la configuration de l'API
is_gemini_configured = False

# Gestionnaire d'erreurs de validation personnalisé
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": f"Erreur de validation: {exc.errors()}"})

# Configuration CORS
origins = ["http://127.0.0.1:5500", "http://localhost:5500", "null", "http://127.0.0.1:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================================
# 5. FONCTIONS AUXILIAIRES
# ===============================================

def calculate_repartition(longueur_libre: float, epaisseur_barreau: float, ecart_maximal: float) -> RepartitionResult:
    if longueur_libre <= 0 or epaisseur_barreau <= 0 or ecart_maximal <= 0:
        return RepartitionResult(nombre_barreaux=0, vide_entre_barreaux_mm=0, jeu_depart_mm=longueur_libre)
    nombre_blocs = longueur_libre / (epaisseur_barreau + ecart_maximal)
    nombre_barreaux = math.ceil(nombre_blocs - 1)
    if nombre_barreaux < 0:
        nombre_barreaux = 0
    nombre_espaces = nombre_barreaux + 1
    if nombre_espaces == 0:
        return RepartitionResult(nombre_barreaux=0, vide_entre_barreaux_mm=0, jeu_depart_mm=longueur_libre)
    longueur_totale_barreaux = nombre_barreaux * epaisseur_barreau
    espacement_reel = (longueur_libre - longueur_totale_barreaux) / nombre_espaces
    if espacement_reel > (ecart_maximal + 1e-9):
        nombre_barreaux += 1
        nombre_espaces = nombre_barreaux + 1
        longueur_totale_barreaux = nombre_barreaux * epaisseur_barreau
        espacement_reel = (longueur_libre - longueur_totale_barreaux) / nombre_espaces
    if nombre_barreaux <= 0:
        return RepartitionResult(nombre_barreaux=0, vide_entre_barreaux_mm=0, jeu_depart_mm=longueur_libre)
    return RepartitionResult(nombre_barreaux=nombre_barreaux, vide_entre_barreaux_mm=espacement_reel, jeu_depart_mm=espacement_reel)

def parse_platine_data(platine_string: str) -> Optional[PlatineDetails]:
    if not platine_string:
        return None
    try:
        parts = {p.split(':')[0].strip().lower(): p.split(':')[1].strip() for p in platine_string.split('/') if ':' in p}
        dims_part = next((p.strip() for p in platine_string.split('/') if ':' not in p), "")
        dims = [float(d) for d in re.findall(r'(\d+\.?\d*)', dims_part)]
        trous = [float(t) for t in re.findall(r'(\d+\.?\d*)', parts.get('trous', ''))]
        entraxes = [float(e) for e in re.findall(r'(\d+\.?\d*)', parts.get('entraxes', ''))]
        return PlatineDetails(longueur=dims[0], largeur=dims[1], epaisseur=dims[2], nombre_trous=int(trous[0]), diametre_trous=trous[1], entraxe_longueur=entraxes[0], entraxe_largeur=entraxes[1])
    except (IndexError, ValueError, KeyError):
        return None

def cleanup_temp_dir(temp_dir: str):
    try:
        shutil.rmtree(temp_dir)
        print(f"DEBUG: Dossier temporaire {temp_dir} supprimé.")
    except Exception as e:
        print(f"ERREUR lors du nettoyage du dossier temporaire {temp_dir}: {e}")


# ===============================================
# 6. ROUTES DE L'API (ENDPOINTS)
# ===============================================

@app.post("/api/process-data")
async def process_data(data: ProjectData):
    try:
        final_morceaux = []
        dims_map = {"poteau": get_deduction_dimension(data.poteau_dims), "liaison": get_deduction_dimension(data.liaison_dims)}
        
        if data.remplissage_type == 'barreaudage_vertical':
            barreau_epaisseur_repartition = get_deduction_dimension(data.barreau_dims)
        elif data.remplissage_type == 'barreaudage_horizontal':
            barreau_epaisseur_repartition = get_thickness_dimension(data.barreau_dims)
        else:
            barreau_epaisseur_repartition = 0

        for i, morceau_data in enumerate(data.morceaux):
            sections_details = []
            structure_items = [item for item in morceau_data.structure if item.type != 'rien']
            if len(structure_items) < 2: continue
            
            for idx, item in enumerate(structure_items):
                if item.type != 'section': continue
                longueur_section = item.longueur
                deduction_gauche, deduction_droite = 0, 0
                if idx > 0:
                    jonction_gauche = structure_items[idx-1]
                    is_extremite_gauche = (idx - 1 == 0)
                    deduction_gauche = dims_map.get(jonction_gauche.type, 0) / (1 if is_extremite_gauche else 2)
                if idx < len(structure_items) - 1:
                    jonction_droite = structure_items[idx+1]
                    is_extremite_droite = (idx + 1 == len(structure_items) - 1)
                    deduction_droite = dims_map.get(jonction_droite.type, 0) / (1 if is_extremite_droite else 2)
                
                longueur_libre = longueur_section - deduction_gauche - deduction_droite
                
                repartition = RepartitionResult(nombre_barreaux=0, vide_entre_barreaux_mm=0, jeu_depart_mm=longueur_libre)
                if data.remplissage_type == 'barreaudage_vertical':
                    repartition = calculate_repartition(longueur_libre, barreau_epaisseur_repartition, data.ecart_barreaux)

                sections_details.append(SectionPlan(longueur_section=longueur_section, longueur_libre=longueur_libre, **repartition.model_dump()))
            
            final_morceaux.append(MorceauPlan(id=i, longueur_totale=sum(s.longueur for s in morceau_data.structure if s.type == 'section' and s.longueur is not None), angle=morceau_data.angle, structure=morceau_data.structure, sections_details=sections_details))
        
        nomenclature = []
        total_poteaux, total_liaisons = 0, 0
        for m in data.morceaux:
            for s_item in m.structure:
                if s_item.type == 'poteau': total_poteaux +=1
                elif s_item.type == 'liaison': total_liaisons +=1
        if total_poteaux > 0: nomenclature.append(NomenclatureItem(item="Poteaux", details=data.poteau_dims, quantite=total_poteaux, longueur_unitaire_mm=data.hauteur_totale))
        if total_liaisons > 0: nomenclature.append(NomenclatureItem(item="Liaisons", details=data.liaison_dims, quantite=total_liaisons, longueur_unitaire_mm=data.hauteur_totale))
        total_longueur_lisses = sum(s.longueur_libre for m in final_morceaux for s in m.sections_details)
        if total_longueur_lisses > 0 and len(final_morceaux) > 0:
            nomenclature.append(NomenclatureItem(item="Lisse Haute", details=data.lissehaute_dims, quantite=len(final_morceaux), longueur_unitaire_mm=round(total_longueur_lisses/len(final_morceaux))))
            nomenclature.append(NomenclatureItem(item="Lisse Basse", details=data.lissebasse_dims, quantite=len(final_morceaux), longueur_unitaire_mm=round(total_longueur_lisses/len(final_morceaux))))
        
        remplissage_details = None
        if data.remplissage_type == 'barreaudage_vertical':
            total_barreaux = sum(s.nombre_barreaux for m in final_morceaux for s in m.sections_details)
            if total_barreaux > 0:
                epaisseur_lisse_haute = get_thickness_dimension(data.lissehaute_dims)
                epaisseur_lisse_basse = get_thickness_dimension(data.lissebasse_dims)
                longueur_unitaire_barreau = data.hauteur_totale - data.hauteur_lisse_basse - epaisseur_lisse_haute - epaisseur_lisse_basse
                nomenclature.append(NomenclatureItem(item="Barreaux", details=data.barreau_dims, quantite=total_barreaux, longueur_unitaire_mm=round(longueur_unitaire_barreau)))
        
        elif data.remplissage_type == 'barreaudage_horizontal':
            hauteur_disponible = data.hauteur_totale - data.hauteur_lisse_basse - get_thickness_dimension(data.lissehaute_dims) - get_thickness_dimension(data.lissebasse_dims)
            remplissage_details = calculate_repartition(hauteur_disponible, barreau_epaisseur_repartition, data.ecart_barreaux)
            
            if remplissage_details and remplissage_details.nombre_barreaux > 0:
                barreaux_par_longueur = {}
                for m in final_morceaux:
                    for s in m.sections_details:
                        longueur = round(s.longueur_libre)
                        if longueur > 0:
                            barreaux_par_longueur[longueur] = barreaux_par_longueur.get(longueur, 0) + 1
                
                for longueur, nb_sections in barreaux_par_longueur.items():
                    nomenclature.append(NomenclatureItem(item=f"Barreaux L={longueur}mm", details=data.barreau_dims, quantite=remplissage_details.nombre_barreaux * nb_sections, longueur_unitaire_mm=longueur))
        
        platine_details = None
        if data.type_fixation == 'platine' and data.platine_dimensions and data.platine_trous and data.platine_entraxes:
            full_platine_string = f"{data.platine_dimensions} / Trous:{data.platine_trous} / Entraxes:{data.platine_entraxes}"
            platine_details = parse_platine_data(full_platine_string)
        
        final_data = FinalPlanData(titre_plan=data.titre_plan, nom_client=data.nom_client, date_chantier=data.date_chantier, description_projet=f"Garde-corps détaillé en {data.nombre_morceaux} morceau(x).", nomenclature=nomenclature, morceaux=final_morceaux, hauteur_totale=data.hauteur_totale, hauteur_lisse_basse=data.hauteur_lisse_basse, poteau_dims=data.poteau_dims, liaison_dims=data.liaison_dims, lissehaute_dims=data.lissehaute_dims, lissebasse_dims=data.lissebasse_dims, barreau_dims=data.barreau_dims, platine_details=platine_details, remplissage_type=data.remplissage_type, remplissage_details=remplissage_details)
        return {"status": "success", "data": final_data.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traitement: {str(e)}")

@app.post("/api/parse-text", response_model=ParsedFormData)
async def parse_text_to_form(data: DescriptionData):
    global is_gemini_configured
    if not genai:
        raise HTTPException(status_code=503, detail="Le service d'analyse IA n'est pas disponible (module non installé).")

    if not is_gemini_configured:
        api_key = os.getenv("MA_CLE_GEMINI")
        if not api_key:
            raise HTTPException(status_code=503, detail="La clé d'API MA_CLE_GEMINI n'est pas configurée sur le serveur.")
        try:
            genai.configure(api_key=api_key)
            is_gemini_configured = True
            print("API Gemini configurée avec succès.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la configuration de l'API Gemini: {e}")
    
    # Ici, vous mettriez votre logique pour appeler le modèle Gemini avec le texte
    # Pour l'instant, c'est un placeholder
    print(f"Analyse du texte demandée: {data.description}")
    return ParsedFormData() # Retourne un formulaire vide pour l'exemple

@app.post("/api/analyze-schema", response_model=ParsedFormData)
async def analyze_schema(data: SchemaData):
    global is_gemini_configured
    if not genai or not Image or not io:
        raise HTTPException(status_code=503, detail="Le service d'analyse d'image n'est pas disponible (modules manquants).")

    if not is_gemini_configured:
        api_key = os.getenv("MA_CLE_GEMINI")
        if not api_key:
            raise HTTPException(status_code=503, detail="La clé d'API MA_CLE_GEMINI n'est pas configurée sur le serveur.")
        try:
            genai.configure(api_key=api_key)
            is_gemini_configured = True
            print("API Gemini configurée avec succès.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la configuration de l'API Gemini: {e}")

    # Ici, vous mettriez votre logique pour appeler le modèle Gemini avec l'image
    # Pour l'instant, c'est un placeholder
    print("Analyse du schéma demandée.")
    return ParsedFormData() # Retourne un formulaire vide pour l'exemple

@app.post("/api/draw-pdf")
async def draw_pdf_plan(data: FinalPlanData):
    try:
        filepath = creer_plan_pdf(data.model_dump())
        if filepath:
            return FileResponse(path=filepath, media_type='application/pdf', filename=f"{data.titre_plan}.pdf")
        raise HTTPException(status_code=500, detail="La création du PDF a échoué.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du dessin PDF: {str(e)}")

@app.post("/api/draw-dxf")
async def draw_dxf_plan(data: FinalPlanData):
    try:
        doc = creer_plan_dxf(data.model_dump())
        if not doc:
            raise HTTPException(status_code=500, detail="La création du document DXF a échoué.")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmpfile:
            doc.saveas(tmpfile.name)
            return FileResponse(path=tmpfile.name, media_type='application/vnd.dxf', filename=f"{data.titre_plan}.dxf")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du plan DXF: {str(e)}")

# La fonctionnalité DWG est désactivée pour le déploiement car elle dépend d'un programme Windows
# @app.post("/api/draw-dwg")
# async def draw_dwg_plan(data: FinalPlanData, background_tasks: BackgroundTasks):
#     if not Path(ODA_CONVERTER_PATH).is_file():
#         raise HTTPException(status_code=501, detail=f"Convertisseur DWG non trouvé à l'emplacement: {ODA_CONVERTER_PATH}")

#     temp_dir = tempfile.mkdtemp()
#     background_tasks.add_task(cleanup_temp_dir, temp_dir)

#     try:
#         input_folder = Path(temp_dir) / "input"
#         output_folder = Path(temp_dir) / "output"
#         input_folder.mkdir()
#         output_folder.mkdir()

#         sanitized_title = re.sub(r'[\\/*?:"<>|]', "", data.titre_plan).replace(" ", "_")
#         input_dxf_path = input_folder / f"{sanitized_title}.dxf"
        
#         doc = creer_plan_dxf(data.model_dump())
#         if not doc:
#             raise HTTPException(status_code=500, detail="La création du document DXF a échoué avant conversion.")
        
#         doc.saveas(input_dxf_path)

#         command = [
#             f'"{ODA_CONVERTER_PATH}"', 
#             f'"{str(input_folder)}"', 
#             f'"{str(output_folder)}"', 
#             "ACAD2018", 
#             "DWG", 
#             "0",
#             "1",
#             "*.DXF"
#         ]
        
#         result = subprocess.run(' '.join(command), shell=True, check=False, capture_output=True, text=True, timeout=30)
        
#         if result.returncode != 0:
#             error_details = result.stderr or "Aucun détail d'erreur fourni par le convertisseur."
#             raise HTTPException(status_code=500, detail=f"La conversion en DWG a échoué. Détails: {error_details}")

#         output_dwg_path = output_folder / f"{sanitized_title}.dwg"
        
#         time.sleep(1)

#         if output_dwg_path.is_file():
#             return FileResponse(
#                 path=str(output_dwg_path),
#                 media_type='application/vnd.dwg',
#                 filename=f"{data.titre_plan}.dwg"
#             )
#         else:
#             raise HTTPException(status_code=500, detail="Le convertisseur s'est terminé sans erreur, mais le fichier DWG de sortie est introuvable.")

#     except Exception as e:
#         cleanup_temp_dir(temp_dir)
#         raise HTTPException(status_code=500, detail=f"Une erreur inattendue est survenue pendant le processus DWG: {str(e)}")


# ===============================================
# 7. SERVIR LE FRONTEND (à la toute fin)
# ===============================================

@app.get("/")
async def read_root():
    """Sert la page d'accueil de l'application."""
    return FileResponse(BASE_DIR / "frontend" / "index.html")

app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")