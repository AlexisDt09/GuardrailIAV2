document.addEventListener('DOMContentLoaded', () => {
    // --- REFERENCES AUX ELEMENTS DU DOM ---
    const tabForm = document.getElementById('tab-form');
    const tabIa = document.getElementById('tab-ia');
    const tabSchema = document.getElementById('tab-schema');
    const contentForm = document.getElementById('content-form');
    const contentIa = document.getElementById('content-ia');
    const contentSchema = document.getElementById('content-schema');
    
    const gardeCorpsForm = document.getElementById('gardeCorpsForm');
    const iaForm = document.getElementById('iaForm');
    const schemaForm = document.getElementById('schemaForm');
    const schemaFile = document.getElementById('schemaFile');
    const imagePreview = document.getElementById('imagePreview');

    const resultatSection = document.getElementById('resultat');
    const nombreMorceauxInput = document.getElementById('nombre_morceaux');
    const morceauxIdentiquesRadios = document.querySelectorAll('input[name="morceaux_identiques"]');
    const morceauxContainer = document.getElementById('morceaux_container');

    const API_BASE_URL = 'http://127.0.0.1:8000';
    let dernierePropositionComplete = null;

    // --- GESTION DES ONGLETS ---
    const tabs = [
        { btn: tabForm, content: contentForm },
        { btn: tabIa, content: contentIa },
        { btn: tabSchema, content: contentSchema }
    ];

    tabs.forEach(tab => {
        if (tab.btn) {
            tab.btn.addEventListener('click', () => {
                tabs.forEach(t => {
                    if (t.content) t.content.classList.add('hidden');
                    if (t.btn) {
                        t.btn.classList.remove('text-indigo-600', 'border-indigo-600');
                        t.btn.classList.add('text-slate-500', 'hover:text-slate-700');
                    }
                });
                if (tab.content) tab.content.classList.remove('hidden');
                if (tab.btn) {
                    tab.btn.classList.add('text-indigo-600', 'border-indigo-600');
                    tab.btn.classList.remove('text-slate-500', 'hover:text-slate-700');
                }
            });
        }
    });

    // --- GESTION SAUVEGARDE/CHARGEMENT PROJET ---
    const ctaContainer = gardeCorpsForm.querySelector('.cta-container');
    if (ctaContainer) {
        const saveLoadContainer = document.createElement('div');
        saveLoadContainer.className = 'flex justify-center gap-4 mt-4';
        saveLoadContainer.innerHTML = `
            <button id="saveProjectBtn" type="button" class="px-4 py-2 text-sm font-medium text-white bg-gray-600 rounded-md hover:bg-gray-700">Sauvegarder le projet</button>
            <button id="loadProjectBtn" type="button" class="px-4 py-2 text-sm font-medium text-white bg-gray-600 rounded-md hover:bg-gray-700">Charger le dernier projet</button>
        `;
        ctaContainer.parentNode.insertBefore(saveLoadContainer, ctaContainer);

        document.getElementById('saveProjectBtn').addEventListener('click', () => {
            const formData = new FormData(gardeCorpsForm);
            const data = Object.fromEntries(formData.entries());
            localStorage.setItem('gardeCorpsProject', JSON.stringify(data));
            alert('Projet sauvegardé !');
        });

        document.getElementById('loadProjectBtn').addEventListener('click', () => {
            const savedData = localStorage.getItem('gardeCorpsProject');
            if (savedData) {
                prefillForm(JSON.parse(savedData));
                alert('Projet chargé !');
            } else {
                alert('Aucun projet sauvegardé trouvé.');
            }
        });
    }


    // --- FONCTIONS DE LOGIQUE METIER ---

    function prefillForm(data) {
        for (const key in data) {
            if (data[key] !== null && !key.startsWith('morceau_')) {
                const input = gardeCorpsForm.querySelector(`[name="${key}"]`);
                if (input) {
                    if (input.type === 'radio') {
                        const radioToSelect = gardeCorpsForm.querySelector(`[name="${key}"][value="${data[key]}"]`);
                        if (radioToSelect) radioToSelect.checked = true;
                    } else {
                        input.value = data[key];
                    }
                }
            }
        }
        
        const nbMorceaux = parseInt(data.nombre_morceaux, 10) || 1;
        nombreMorceauxInput.value = nbMorceaux;
        renderForm(); // Important de render avant de remplir les morceaux

        const sontIdentiques = data.morceaux_identiques === 'oui';
        const loopCount = sontIdentiques ? 1 : nbMorceaux;

        for (let i = 0; i < loopCount; i++) {
            const angleInput = document.getElementById(`morceau_${i}_angle`);
            if (angleInput && data[`morceau_${i}_angle`]) {
                angleInput.value = data[`morceau_${i}_angle`];
            }

            const nbSectionsInput = document.getElementById(`morceau_${i}_nombre_sections`);
            const nbSections = parseInt(data[`morceau_${i}_nombre_sections`], 10) || 1;
            if (nbSectionsInput) {
                nbSectionsInput.value = nbSections;
                renderStructure(i, nbSectionsInput.closest('fieldset').querySelector('.mt-4'), nbSections);
            }
            
            for (let j = 0; j <= nbSections; j++) {
                const jonctionInput = document.querySelector(`[name="morceau_${i}_jonction_${j}"]`);
                if(jonctionInput && data[`morceau_${i}_jonction_${j}`]) {
                    jonctionInput.value = data[`morceau_${i}_jonction_${j}`];
                }
                if(j < nbSections) {
                    const longueurInput = document.querySelector(`[name="morceau_${i}_section_longueur_${j}"]`);
                    if(longueurInput && data[`morceau_${i}_section_longueur_${j}`]) {
                        longueurInput.value = data[`morceau_${i}_section_longueur_${j}`];
                    }
                }
            }
        }
    }

    // --- GESTION DES FORMULAIRES ---

    if (schemaFile) {
        schemaFile.addEventListener('change', () => {
            const file = schemaFile.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.innerHTML = `<img src="${e.target.result}" class="max-h-full max-w-full object-contain">`;
                };
                reader.readAsDataURL(file);
            } else {
                imagePreview.innerHTML = '<span class="text-slate-500">Prévisualisation de l\'image</span>';
            }
        });
    }

    async function handleIaFormSubmit(event) {
        event.preventDefault();
        // ... (logique IA inchangée)
    }

    async function handleSchemaFormSubmit(event) {
        event.preventDefault();
        // ... (logique Schéma inchangée)
    }
    
    // --- LOGIQUE DU FORMULAIRE DYNAMIQUE ---
    function createJunctionSelector(name) {
        const select = document.createElement('select');
        select.name = name;
        select.className = 'w-full p-2 border border-slate-300 rounded-md bg-slate-50';
        select.innerHTML = `<option value="rien">Rien</option><option value="poteau" selected>Poteau</option><option value="liaison">Liaison</option>`;
        return select;
    }
    function createSectionInput(morceauIndex, sectionIndex) {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2';
        const label = document.createElement('label');
        label.textContent = `Long. Section ${sectionIndex + 1} (mm):`;
        label.className = 'text-sm text-slate-600';
        const input = document.createElement('input');
        input.type = 'number';
        input.name = `morceau_${morceauIndex}_section_longueur_${sectionIndex}`;
        input.className = 'w-full p-2 border border-slate-300 rounded-md';
        input.placeholder = 'Ex: 1500';
        input.required = true;
        input.min = 1;
        div.appendChild(label);
        div.appendChild(input);
        return div;
    }
    function createMorceauUI(morceauIndex, isIdenticalTemplate = false) {
        const fieldset = document.createElement('fieldset');
        fieldset.className = 'p-4 border border-slate-200 rounded-lg';
        const legend = document.createElement('legend');
        legend.className = 'text-lg font-semibold text-slate-700 px-2';
        legend.textContent = isIdenticalTemplate ? 'Détail du morceau type' : `Détail du Morceau ${morceauIndex + 1}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'space-y-4';

        const settingsGrid = document.createElement('div');
        settingsGrid.className = 'grid grid-cols-1 md:grid-cols-2 gap-4';

        const sectionsCountDiv = document.createElement('div');
        sectionsCountDiv.innerHTML = `<label for="morceau_${morceauIndex}_nombre_sections" class="block text-sm font-medium text-slate-600 mb-1">Nombre de sections</label><input type="number" id="morceau_${morceauIndex}_nombre_sections" name="morceau_${morceauIndex}_nombre_sections" value="1" min="1" required class="w-full p-2 border border-slate-300 rounded-md">`;
        
        const angleDiv = document.createElement('div');
        angleDiv.innerHTML = `<label for="morceau_${morceauIndex}_angle" class="block text-sm font-medium text-slate-600 mb-1">Angle (degrés)</label><input type="number" id="morceau_${morceauIndex}_angle" name="morceau_${morceauIndex}_angle" value="0" step="0.1" class="w-full p-2 border border-slate-300 rounded-md">`;

        settingsGrid.appendChild(sectionsCountDiv);
        settingsGrid.appendChild(angleDiv);

        const structureContainer = document.createElement('div');
        structureContainer.className = 'mt-4 p-4 bg-slate-50 rounded-md space-y-3';

        contentDiv.appendChild(settingsGrid);
        contentDiv.appendChild(structureContainer);
        fieldset.appendChild(legend);
        fieldset.appendChild(contentDiv);

        const sectionsCountInput = sectionsCountDiv.querySelector('input');
        sectionsCountInput.addEventListener('input', () => {
            renderStructure(morceauIndex, structureContainer, parseInt(sectionsCountInput.value, 10));
        });

        renderStructure(morceauIndex, structureContainer, parseInt(sectionsCountInput.value, 10));
        return fieldset;
    }
    function renderStructure(morceauIndex, container, count) {
        container.innerHTML = '';
        if (isNaN(count) || count < 1) return;
        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-1 md:grid-cols-2 gap-4 items-end';
        const startDiv = document.createElement('div');
        startDiv.innerHTML = '<label class="text-sm font-medium text-slate-600">Début</label>';
        startDiv.appendChild(createJunctionSelector(`morceau_${morceauIndex}_jonction_0`));
        grid.appendChild(startDiv);
        for (let i = 0; i < count; i++) {
            grid.appendChild(createSectionInput(morceauIndex, i));
            const junctionDiv = document.createElement('div');
            junctionDiv.innerHTML = `<label class="text-sm font-medium text-slate-600">Jonction ${i + 1}</label>`;
            junctionDiv.appendChild(createJunctionSelector(`morceau_${morceauIndex}_jonction_${i + 1}`));
            grid.appendChild(junctionDiv);
        }
        container.appendChild(grid);
    }
    function renderForm() {
        morceauxContainer.innerHTML = '';
        const nbMorceaux = parseInt(nombreMorceauxInput.value, 10);
        const sontIdentiques = document.querySelector('input[name="morceaux_identiques"]:checked').value === 'oui';
        if (isNaN(nbMorceaux) || nbMorceaux < 1) return;
        if (sontIdentiques) {
            morceauxContainer.appendChild(createMorceauUI(0, true));
        } else {
            for (let i = 0; i < nbMorceaux; i++) {
                morceauxContainer.appendChild(createMorceauUI(i, false));
            }
        }
    }
    
    // --- FONCTIONS DE SOUMISSION ET GESTION DES RÉSULTATS ---

    async function handleFormSubmit(event) {
        event.preventDefault();
        if (!gardeCorpsForm.checkValidity()) {
            gardeCorpsForm.reportValidity();
            return;
        }
        resultatSection.innerHTML = `<div class="p-4 text-center bg-blue-100 text-blue-800 rounded-lg"><p class="font-semibold">Calcul en cours...</p></div>`;
        
        const formData = new FormData(gardeCorpsForm);
        const rawData = Object.fromEntries(formData.entries());

        const projectData = {
            titre_plan: rawData.titre_plan,
            nom_client: rawData.nom_client,
            date_chantier: rawData.date_chantier,
            hauteur_totale: parseInt(rawData.hauteur_totale, 10),
            hauteur_lisse_basse: parseInt(rawData.hauteur_lisse_basse, 10),
            poteau_dims: rawData.poteau_dims,
            liaison_dims: rawData.liaison_dims || "", 
            lissehaute_dims: rawData.lissehaute_dims,
            lissebasse_dims: rawData.lissebasse_dims,
            barreau_dims: rawData.barreau_dims,
            ecart_barreaux: parseInt(rawData.ecart_barreaux, 10),
            type_fixation: rawData.type_fixation,
            remplissage_type: rawData.remplissage_type,
            platine_dimensions: rawData.platine_dimensions || null,
            platine_trous: rawData.platine_trous || null,
            platine_entraxes: rawData.platine_entraxes || null,
            nombre_morceaux: parseInt(rawData.nombre_morceaux, 10),
            morceaux_identiques: rawData.morceaux_identiques,
            morceaux: [] 
        };

        const nbMorceaux = projectData.nombre_morceaux;
        const sontIdentiques = projectData.morceaux_identiques === 'oui';

        let templateMorceau = null;
        if (sontIdentiques) {
            const nbSections = parseInt(rawData.morceau_0_nombre_sections, 10);
            const angle = parseFloat(rawData.morceau_0_angle) || 0;
            templateMorceau = {
                nombre_sections: nbSections,
                angle: angle,
                structure: []
            };
            for (let j = 0; j <= nbSections; j++) {
                templateMorceau.structure.push({ type: rawData[`morceau_0_jonction_${j}`] });
                if (j < nbSections) {
                    const longueur = parseFloat(rawData[`morceau_0_section_longueur_${j}`]);
                    templateMorceau.structure.push({ type: 'section', longueur: isNaN(longueur) ? 0 : longueur });
                }
            }
        }

        for (let i = 0; i < nbMorceaux; i++) {
            if (sontIdentiques) {
                projectData.morceaux.push(JSON.parse(JSON.stringify(templateMorceau)));
            } else {
                const nbSections = parseInt(rawData[`morceau_${i}_nombre_sections`], 10);
                const angle = parseFloat(rawData[`morceau_${i}_angle`]) || 0;
                const morceau = {
                    nombre_sections: nbSections,
                    angle: angle,
                    structure: []
                };
                for (let j = 0; j <= nbSections; j++) {
                    morceau.structure.push({ type: rawData[`morceau_${i}_jonction_${j}`] });
                    if (j < nbSections) {
                        const longueur = parseFloat(rawData[`morceau_${i}_section_longueur_${j}`]);
                        morceau.structure.push({ type: 'section', longueur: isNaN(longueur) ? 0 : longueur });
                    }
                }
                projectData.morceaux.push(morceau);
            }
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/process-data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(projectData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Erreur inconnue du serveur.');
            }
            
            const result = await response.json();
            dernierePropositionComplete = result.data;
            displayResults(result.data);
        } catch (error) {
            resultatSection.innerHTML = `<div class="p-4 text-center bg-red-100 text-red-800 rounded-lg"><p><b>Erreur :</b> ${error.message}</p></div>`;
        }
    }

    function displayResults(data) {
        let nomenclatureHtml = '';
        if (data.nomenclature && data.nomenclature.length > 0) {
            const tableRows = data.nomenclature.map(item => `<tr class="border-b border-slate-200 last:border-b-0"><td class="p-3">${item.item}</td><td class="p-3 text-slate-600">${item.details}</td><td class="p-3 text-center">${item.quantite}</td><td class="p-3 text-right">${item.longueur_unitaire_mm} mm</td></tr>`).join('');
            nomenclatureHtml = `<div><h3 class="font-bold text-lg text-slate-700 mt-6 mb-2">Nomenclature</h3><div class="overflow-hidden border border-slate-200 rounded-lg"><table class="min-w-full bg-white text-sm"><thead class="bg-slate-50"><tr><th class="p-3 text-left font-semibold text-slate-600">Élément</th><th class="p-3 text-left font-semibold text-slate-600">Détails</th><th class="p-3 text-center font-semibold text-slate-600">Quantité</th><th class="p-3 text-right font-semibold text-slate-600">Longueur Unitaire</th></tr></thead><tbody>${tableRows}</tbody></table></div></div>`;
        }
        let planDetailsHtml = '';
        if (data.morceaux && data.morceaux.length > 0) {
            planDetailsHtml = data.morceaux.map((morceau, index) => {
                const angleText = morceau.angle !== 0 ? ` / Angle: ${morceau.angle}°` : '';
                const sectionRows = morceau.sections_details.map((section, secIndex) => `<tr class="border-b border-slate-200 last:border-b-0"><td class="p-2 text-center">${secIndex + 1}</td><td class="p-2 text-right">${section.longueur_section.toFixed(1)} mm</td><td class="p-2 text-right">${section.longueur_libre.toFixed(1)} mm</td><td class="p-2 text-center">${section.nombre_barreaux}</td><td class="p-2 text-right">${section.vide_entre_barreaux_mm.toFixed(1)} mm</td><td class="p-2 text-right">${section.jeu_depart_mm.toFixed(1)} mm</td></tr>`).join('');
                return `<div class="mt-4"><h4 class="font-semibold text-md text-slate-700">Détail du Morceau ${index + 1} (L: ${morceau.longueur_totale.toFixed(1)} mm${angleText})</h4><div class="overflow-hidden border border-slate-200 rounded-lg mt-1"><table class="min-w-full bg-white text-xs"><thead class="bg-slate-50"><tr><th class="p-2 text-center">Section</th><th class="p-2 text-right">Long. Section</th><th class="p-2 text-right">Long. Libre</th><th class="p-2 text-center">Nb. Barreaux</th><th class="p-2 text-right">Vide Barreaux</th><th class="p-2 text-right">Jeu Départ</th></tr></thead><tbody>${sectionRows}</tbody></table></div></div>`;
            }).join('');
        }
        
        resultatSection.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow-inner border border-slate-200 text-left space-y-4">
                <h2 class="text-2xl font-bold text-slate-800 border-b pb-2">Proposition Générée</h2>
                ${nomenclatureHtml}
                <div>
                    <h3 class="font-bold text-lg text-slate-700 mt-6 mb-2">Plan de Fabrication Détaillé</h3>
                    ${planDetailsHtml}
                </div>
                <div class="text-center pt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
                    <button id="downloadPdfBtn" class="w-full bg-purple-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-purple-700">Télécharger PDF</button>
                    <button id="downloadDxfBtn" class="w-full bg-green-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-green-700">Télécharger DXF</button>
                    <button id="downloadDwgBtn" class="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700">Télécharger DWG</button>
                </div>
            </div>`;
        
        document.getElementById('downloadPdfBtn').addEventListener('click', () => handleDownload('pdf'));
        document.getElementById('downloadDxfBtn').addEventListener('click', () => handleDownload('dxf'));
        document.getElementById('downloadDwgBtn').addEventListener('click', () => handleDownload('dwg'));
    }
    
    function sanitizeFilename(name) {
        if (!name) return 'plan';
        return name.replace(/[^a-z0-9_.\-]/gi, '_').toLowerCase();
    }

    async function handleDownload(type) {
        if (!dernierePropositionComplete) return;

        const btnId = `download${type.charAt(0).toUpperCase() + type.slice(1)}Btn`;
        const btn = document.getElementById(btnId);
        let endpoint, extension;

        switch (type) {
            case 'pdf':
                endpoint = '/api/draw-pdf';
                extension = 'pdf';
                break;
            case 'dxf':
                endpoint = '/api/draw-dxf';
                extension = 'dxf';
                break;
            case 'dwg':
                endpoint = '/api/draw-dwg';
                extension = 'dwg';
                break;
            default:
                return;
        }
        
        btn.textContent = `Génération ${extension.toUpperCase()}...`;
        btn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dernierePropositionComplete),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Erreur serveur ${response.status}`);
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${sanitizeFilename(dernierePropositionComplete.titre_plan)}.${extension}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

        } catch (error) {
            alert(`Erreur lors du téléchargement: ${error.message}`);
        } finally {
            btn.textContent = `Télécharger ${extension.toUpperCase()}`;
            btn.disabled = false;
        }
    }

    // --- EVENT LISTENERS ---
    nombreMorceauxInput.addEventListener('input', renderForm);
    morceauxIdentiquesRadios.forEach(radio => radio.addEventListener('change', renderForm));
    if(gardeCorpsForm) gardeCorpsForm.addEventListener('submit', handleFormSubmit);
    if(iaForm) iaForm.addEventListener('submit', handleIaFormSubmit);
    if(schemaForm) schemaForm.addEventListener('submit', handleSchemaFormSubmit);
    
    // Initial render
    renderForm();
});
