"""Fonctions d'appel aux fournisseurs d'IA : Groq, Gemini, Ollama, xAI."""

import json
import logging
import re
from typing import Optional, List, Dict, Any

import requests
from groq import Groq

try:
    from google import genai
    from google.genai import types
    GOOGLE_NEW_SDK = True
except Exception:
    GOOGLE_NEW_SDK = False

try:
    import google.generativeai as legacy_genai
    GOOGLE_LEGACY_SDK = True
except Exception:
    GOOGLE_LEGACY_SDK = False

logger = logging.getLogger(__name__)


def is_ollama_online(ollama_url: str = "http://localhost:11434") -> bool:
    """Vérifie si le serveur Ollama répond."""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_ollama_version(ollama_url: str = "http://localhost:11434") -> Optional[str]:
    """Récupère la version d'Ollama via l'API."""
    try:
        response = requests.get(f"{ollama_url}/api/version", timeout=2)
        if response.status_code == 200:
            return response.json().get("version")
    except Exception:
        return None
    return None


def call_local_llama(prompt: str, model_name: str, ollama_url: str = "http://localhost:11434", is_json: bool = False) -> Optional[str]:
    """Appelle l'instance locale d'Ollama."""
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json" if is_json else ""
        }
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=90)
        if response.status_code == 200:
            return response.json().get("response")
        else:
            error_data = response.json()
            error_msg = error_data.get("error", response.text)
            if "unknown model architecture" in error_msg.lower() or "mllama" in error_msg.lower():
                logger.error("Erreur d'architecture Ollama")
            else:
                logger.error(f"Erreur Ollama : {error_msg}")
            return None
    except Exception as e:
        logger.error(f"Ollama Local Error: {e}")
        return None


def call_ai_provider(
    prompt: str,
    selected_model: str,
    is_json: bool = False,
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[str]:
    """Fonction centralisée pour appeler Gemini, Groq, xAI ou Ollama.

    Args:
        prompt: Le texte du prompt à envoyer.
        selected_model: Le nom du modèle sélectionné (ex: "Gemini 3.5", "Groq / Llama 3.3").
        is_json: Si True, demande une réponse JSON structurée.
        gemini_api_key: Clé API Gemini du .env.
        xai_api_key: Clé API xAI (Grok) du .env.
        groq_api_key: Clé API Groq du .env.
        ollama_url: URL du serveur Ollama local.
        custom_gemini_key: Clé API Gemini personnalisée saisie par l'utilisateur.

    Returns:
        Texte de la réponse ou None en cas d'erreur.
    """
    active_gemini_key = (custom_gemini_key or gemini_api_key or "").strip()

    try:
        if "Gemini" in selected_model:
            if not active_gemini_key:
                raise Exception("Clé API Gemini manquante.")
            model_id = "gemini-2.0-flash" if "3.5" in selected_model else "gemini-1.5-flash"
            logger.info(f"Appel Gemini AI : {model_id}")

            if GOOGLE_NEW_SDK:
                sdk = "google.genai"
                client = genai.Client(api_key=active_gemini_key)
                config = (
                    types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                        ],
                    )
                    if is_json
                    else types.GenerateContentConfig(
                        temperature=0.7,
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                        ],
                    )
                )
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=config,
                )
            elif GOOGLE_LEGACY_SDK:
                sdk = "google.generativeai"
                legacy_genai.configure(api_key=active_gemini_key)
                model = legacy_genai.GenerativeModel(f"models/{model_id}")
                generation_config = (
                    {"response_mime_type": "application/json", "temperature": 0.1}
                    if is_json
                    else {"temperature": 0.7}
                )
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
            else:
                raise Exception("Aucun SDK Google Generative AI disponible.")

            logger.info(f"[Gemini] Appel réel OK (sdk={sdk})")
            if hasattr(response, "candidates") and response.candidates and response.candidates[0].finish_reason not in (None, 1):
                reason = response.candidates[0].finish_reason
                logger.warning(f"Gemini finish_reason inhabituel : {reason}")
                if reason == 3:
                    raise Exception("L'analyse a été bloquée par les filtres de sécurité de Google.")

            try:
                text = response.text
            except (ValueError, AttributeError):
                if hasattr(response, "candidates") and response.candidates and len(response.candidates[0].content.parts) > 0:
                    text = response.candidates[0].content.parts[0].text
                else:
                    raise Exception("Gemini a refusé de générer du texte pour ce contenu (Filtre de sécurité).")

            if is_json:
                json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
                if json_match:
                    text = json_match.group(1)
            return text

        elif "(Local/dev)" in selected_model:
            model_map = {
                "Llama 3.2 Vision (Local/dev)": "llama3.2-vision",
                "Llama 3.2 (Local/dev)": "llama3.2",
                "Qwen 3 4B (Local/dev)": "qwen3:4b"
            }
            ollama_model = model_map.get(selected_model, "llama3.2")
            return call_local_llama(prompt, ollama_model, ollama_url, is_json=is_json)

        elif "Grok" in selected_model:
            if not xai_api_key:
                raise Exception("Clé API xAI (Grok) non configurée dans le fichier .env")
            headers = {
                "Authorization": f"Bearer {xai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

        else:
            # Groq / Llama 3.3
            if not groq_api_key:
                raise Exception("Clé Groq non configurée")
            client = Groq(api_key=groq_api_key)
            params = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "llama-3.3-70b-versatile",
            }
            if is_json:
                params["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Erreur AI Provider ({selected_model}): {e}")
        raise Exception(err_msg)


"""
Dictionnaire exhaustif de détection de métiers par Regex (Fallback sans IA)
Regroupe plus de 500 intitulés de postes et variantes (Français & Anglais)
répartis sur 22 domaines professionnels (ROME / France Travail).
"""

JOB_DICTIONARY = {
    "Logistique, Transport & Déménagement": [
        r"Déménageur|Déménageuse|Chef\s*d'Équipe\s*Déménagement|Aide-Déménageur",
        r"(?:Préparateur|Préparatrice)\s*de\s*Commandes|Magasinier|Cariste|Manutentionnaire|Agent\s*de\s*Quai|Palettiseur",
        r"Conducteur|Conductrice\s*(?:Routier|SPL|Poids\s*Lourd|Ligne|Super\s*Lourd|Autocar|Bus|Tramway|Train|TGV)",
        r"(?:Chauffeur|Livreur|Chauffeur-Livreur|Livreur\s*Express|Chauffeur\s*VTC|Taximan|Coursier|Chauffeur\s*Lourd)",
        r"Responsable\s*(?:Logistique|Supply\s*Chain|Achats|Exploitation|Entrepôt|Plateforme)",
        r"Affréteur|Dispatcher|Exploitant\s*Transport|Agent\s*d'Escale|Agent\s*de\s*Piste\s*Aéroportuaire",
        r"(?:Acheteur|Acheteuse)\s*(?:IT|Industriel|International|Prestations|Projet|Hors-Production)?",
        r"Gestionnaire\s*de\s*Stock|Approvisionneur|Approvisionneuse",
    ],
    "BTP, Construction & Artisanat du bâtiment": [
        r"Maçon|Maçonne|Coffreur|Coffreuse|Ferrailleur|Bétonneur",
        r"Électricien|Électricienne|Électricien\s*(?:Bâtiment|Tertiaire|Industriel)",
        r"Plombier|Plombière|Chauffagiste|Installateur\s*Thermique|Cuisiste",
        r"Peintre\s*(?:en\s*Bâtiment|Industriel)|Plaquiste|Jointeur|Plâtrier",
        r"Menuisier|Menuisière|Charpentier|Charpentière|Couvreur|Zingueur|Étancheur",
        r"Carreleur|Soliere|Poseur\s*de\s*Parquet|Moquettiste",
        r"Serrurier|Métallier|Miroitier|Vitrier",
        r"Jardinier|Jardinière|Paysagiste|Élagueur|Ouvrier\s*Paysagiste|Agent\s*d'Espaces\s*Verts",
        r"(?:Conducteur|Conductrice)\s*de\s*(?:Travaux|Chantier|Engins)",
        r"Chef\s*de\s*Chantier|Chef\s*d'Équipe\s*BTP|Conducteur\s*d'Opérations",
        r"Métréur|Économiste\s*du\s*Bâtiment|Géomètre|Topographe|Conducteur\s*d'Engins\s*de\s*Chantier",
        r"Dessinateur|Dessinatrice\s*Projeteur|Projeteur\s*BIM|BIM\s*Manager",
        r"Architecte|Architecte\s*d'Intérieur|Urbaniste|Paysagiste-Concepteur",
    ],
    "Tech & Développement": [
        r"(?:Développeur|Développeuse)\s*(?:Web|Full[ -]?Stack|React|Vue|Angular|Node\.?js|Python|Java|JavaScript|PHP|Ruby|Go|Rust|Mobile|iOS|Android|Backend|Frontend|API|Symfony|Laravel|Django|Flask|Spring|C\+\+|C#|\.NET|Embedded|Embarqué|WordPress|Shopify|Webflow)?",
        r"(?:Ingénieur|Ingénieure)\s*(?:Logiciel|Informatique|Développement|Full[ -]?Stack|QA|Test|Validation|R\&D|Systèmes|Conception|Embedded)?",
        r"(?:Scrum\s*Master|Agile\s*Coach|Product\s*Owner|Lead\s*Developer|Tech\s*Lead)",
        r"(?:Intégrateur|Intégratrice)\s*(?:Web|HTML|CSS|CMS)|Webmaster",
    ],
    "Data, Cloud & Cybersécurité": [
        r"Data\s*(?:Scientist|Analyst|Engineer|Architect|Specialist|Consultant|Analyste|Ingénieur)",
        r"Machine\s*Learning\s*(?:Engineer|Scientist)|Ingénieur\s*IA",
        r"DevOps\s*(?:Engineer|Specialist|Consultant|Ingénieur)?|Cloud\s*Engineer|SRE",
        r"Architecte\s*(?:Logiciel|Informatique|Cloud|Solution|Data|Système|Web|Infrastructure|SI|Sécurité)",
        r"(?:Administrateur|Administratrice)\s*(?:Système|Réseaux|Base\s*de\s*Données|Cloud|DevOps|Infrastructure|AWS|Azure|GCP|DBA)",
        r"(?:Expert|Ingénieur|Consultant|Analyste)\s*(?:Cybersécurité|Sécurité\s*SI|SOC|Pentester)",
        r"(?:Technicien|Technicienne)\s*(?:Informatique|Support|Réseau|Système|Helpdesk|Micro-informatique|Proximité)",
    ],
    "Propreté, Entretien & Déchets": [
        r"Agent\s*d'Entretien|Agent\s*de\s*Propreté|Agent\s*de\s*Nettoyage|Femme\s*de\s*Ménage|Homme\s*de\s*Ménage|Technicien\s*de\s*Surface",
        r"Ripeur|Éboueur|Agent\s*de\s*Collecte|Agent\s*de\s*Tri|Agent\s*de\s*Déchèterie",
        r"Laveur\s*de\s*Vitres|Agent\s*d'Entretien\s*Industriel",
        r"Agent\s*de\s*Maintenance|Factotum|Agent\s*des\s*Services\s*Généraux",
    ],
    "Restauration, Hôtellerie & Alimentation": [
        r"Cuisinier|Cuisinière|Chef\s*de\s*Cuisine|Second\s*de\s*Cuisine|Commis\s*de\s*Cuisine|Chef\s*Pâtissier|Pâtissier|Pâtissière",
        r"Boulanger|Boulangère|Boucher|Bouchère|Charcutier|Poissonnerie|Traiteur",
        r"Serveur|Serveuse|Chef\s*de\s*Rang|Maître\s*d'Hôtel|Sommelier|Sommelière|Plongeur|Plongeuse",
        r"Barman|Barmaid|Barista|Garçon\s*de\s*Café",
        r"(?:Réceptionniste|Directeur\s*d'Hôtel|Gouvernant|Gouvernante|Veilleur\s*de\s*Nuit|Valet\s*de\s*Chambre|Femme\s*de\s*Chambre)",
        r"Employé|Employée\s*de\s*Restauration\s*(?:Rapide|Collective)",
    ],
    "Commerce & Grande Distribution": [
        r"(?:Commercial|Commerciale|Attaché(?:e)?\s*Commercial(?:e)?|Ingénieur\s*Commercial)",
        r"(?:Business\s*Developer|BizDev|Account\s*Manager|Key\s*Account\s*Manager|KAM)",
        r"Chef\s*de\s*Secteur|Responsable\s*Commerci(?:al|ale)|Directeur\s*Commercial",
        r"(?:Responsable|Conseiller|Conseillère)\s*(?:Clientèle|Vente|Service\s*Client)",
        r"(?:Vendeur|Vendeuse|Caissier|Caissière|Hôte|Hôtesse\s*de\s*Caisse|Chef\s*de\s*Rayon|Employé\s*de\s*Rayon|Mise\s*en\s*Rayon)",
        r"Téléconseiller|Téléconseillère|Agent\s*de\s*Call\s*Center|Télévendeur",
    ],
    "Industrie, Maintenance & Production": [
        r"(?:Ingénieur|Ingénieure)\s*(?:Mécanique|Électrique|Industriel|Qualité|Process|Production|QSE|HSE|Matériaux|Automatisme)",
        r"(?:Technicien|Technicienne)\s*(?:Maintenance|Qualité|Usinage|Automatisme|Essais|Méthodes|Génie\s*Industriel)",
        r"Opérateur|Opératrice\s*(?:de\s*Saisie|de\s*Production|d'Usinage|Assemblage|Ligne|Machine)",
        r"Manoeuvre|Usineur|Oustilleur|Chaudronnier|Soudure|Soudeur|Soudeuse|Tuyauteur",
        r"Dessinateur|Dessinatrice\s*Industriel|Concepteur\s*Mécanique",
    ],
    "Administratif & Secrétariat": [
        r"(?:Assistant|Assistante)\s*(?:de\s*Gestion|Direction|Administrative|Commerciale|Opérationnelle|Polyvalente)",
        r"Secrétaire\s*(?:Médicale|Juridique|Comptable|De\s*Direction|Bureautique)?",
        r"Office\s*Manager|Gestionnaire\s*Administratif",
        r"Agent\s*d'Accueil|Standardiste|Hôte|Hôtesse\s*d'Accueil",
    ],
    "Finance & Comptabilité": [
        r"(?:Comptable|Aide-Comptable|Chef\s*Comptable|Expert-Comptable|Comptable\s*Fournisseurs|Comptable\s*Clients)",
        r"Gestionnaire\s*de\s*Paie|Collaborateur\s*Comptable|Gestionnaire\s*Comptable",
        r"(?:Contrôleur|Contrôleuse)\s*de\s*Gestion|Analyste\s*FP\&A",
        r"Analyste\s*(?:Financier|Crédit|Risque|M\&A|KYC)",
        r"(?:Directeur|Directrice|Responsable)\s*(?:Financier|RAF|DAF|Trésorerie)",
        r"Trésorier|Trésorière|Auditeur|Auditrice",
        r"Conseiller\s*(?:Bancaire|Financier|Patrimoine)",
    ],
    "Ressources Humaines": [
        r"(?:Responsable|Chargé(?:e)?)\s*(?:des\s*Ressources\s*Humaines|du\s*Recrutement|RH|GPEC|Sourcing)",
        r"(?:Talent\s*Acquisition\s*Specialist|Recruteur|Recruteuse|Chasseur\s*de\s*Têtes)",
        r"(?:Assistant|Assistante)\s*RH|Gestionnaire\s*(?:RH|ADP)",
        r"Directeur\s*des\s*Ressources\s*Humaines|DRH",
    ],
    "Digital, Design & Marketing": [
        r"(?:UX|UI|UX/UI)\s*(?:Designer|Researcher)",
        r"Designer\s*(?:Graphique|Web|Digital|Produit|Interface|Motion|3D|Product)",
        r"(?:Graphiste|Infographiste|Directeur\s*Artistique|DA|Motion\s*Designer)",
        r"Chef\s*de\s*Projet\s*(?:Digital|Web|Marketing|Communication|E-commerce|SEO)",
        r"(?:Community\s*Manager|Social\s*Media\s*Manager|Content\s*Manager)",
        r"(?:Responsable|Chargé(?:e)?)\s*de\s*(?:Communication|Marketing|SEO|SEA|E-commerce|Growth|Acquisition)",
        r"Growth\s*Hacker|Traffic\s*Manager|Rédacteur\s*Web|Copywriter",
    ],
    "Management & Conseil": [
        r"(?:Chef|Cheffe)\s*de\s*Projet\s*(?:Informatique|SI|Digital|Data|Organisation|Transverse|Industriel|PMO|AMOA)?",
        r"(?:Project\s*Manager|Business\s*Analyst|Product\s*Manager)",
        r"(?:Consultant|Consultante)\s*(?:Senior|Junior)?\s*(?:en\s*Management|Stratégie|Organisation|SI|RH|IT)",
        r"(?:Directeur|Directrice)\s*(?:Général|Technique|CTO|CIO|DSI|Marketing|RH|Commercial|Financier|CFO|COO)",
    ],
    "Santé & Médical": [
        r"(?:Infirmier|Infirmière|Infirmier\s*Anesthésiste|IBODE|IADE|Puéricultrice)",
        r"Aide-Soignant|Aide-Soignante|Auxiliaire\s*de\s*Puériculture",
        r"(?:Médecin|Pharmacien|Pharmacienne|Chirurgien|Dentiste|Sage-Femme)",
        r"Kinésithérapeute|Ergothérapeute|Orthophoniste|Ostéopathe|Psychologue|Psychiatre",
        r"Manipulateur\s*Radio|Technicien\s*de\s*Laboratoire\s*Médical",
        r"Secrétaire\s*Médicale|Brancardier|Ambulancier|Ambulancière",
    ],
    "Social & Enfance": [
        r"Éducateur|Éducatrice\s*(?:Spécialisé(?:e)?|Jeunes\s*Enfants)",
        r"Assistant|Assistante\s*Sociale|Conseiller\s*ESF",
        r"Auxiliaire\s*de\s*Vie|Aide\s*à\s*Domicile|Accompagnant\s*Éducatif|ATSEM|Nounou|Garde\s*d'Enfants",
        r"Animateur|Animatrice\s*(?:Socioculturel|Scolaire|Enfants|Périscolaire)",
    ],
    "Enseignement & Formation": [
        r"(?:Professeur|Professeure|Enseignant|Enseignante)\s*(?:des\s*Écoles|de\s*Français|d'Anglais|de\s*Mathématiques|de\s*Physique)?",
        r"Formateur|Formatrice\s*(?:Professionnel|Consultant|Adultes|Tech)?",
        r"AESH|Auxiliaire\s*de\s*Vie\s*Scolaire|CPE|Conseiller\s*Principal\s*d'Éducation",
        r"Enseignant-Chercheur|Maître\s*de\s*Conférences",
    ],
    "Sécurité & Gardiennage": [
        r"Agent\s*de\s*Sécurité|Agent\s*CQP|Agent\s*Master|Pompier|SSIAP|SSIAP\s*1|SSIAP\s*2|SSIAP\s*3",
        r"Inspecteur\s*de\s*Sécurité|Agent\s*de\s*Sûreté|Maitre-Chien|Agent\s*Cynophile",
        r"Gendarme|Policier|Agent\s*de\s*Police\s*Municipale|Militaire|Vigile|Gardien\s*d'Immeuble",
    ],
    "Droit & Juridique": [
        r"(?:Juriste)\s*(?:Droit\s*des\s*Affaires|Droit\s*Social|Droit\s*du\s*Travail|Intellectuel|RGPD|DPO)?",
        r"Avocat|Avocate|Notaire|Clerc\s*de\s*Notaire|Huissier|Commissaire\s*de\s*Justice",
        r"Fiscaliste|Compliance\s*Officer|Assistante\s*Juridique",
    ],
    "Esthétique, Coiffure & Mode": [
        r"Coiffeur|Coiffeuse|Barbier",
        r"Esthéticien|Esthéticienne|Prothésiste\s*Ongulaire|Maquilleur|Maquilleuse",
        r"Couturier|Couturière|Styliste|Modéliste",
    ],
    "Agriculture, Élevage & Pêche": [
        r"Ouvrier\s*Agricole|Aide\s*Agricole|Arboriculteur|Viticulteur|Vendangeur",
        r"Éleveur|Éleveuse|Tractoriste|Conducteur\s*d'Engins\s*Agricoles",
        r"Pêcheur|Marin-Pêcheur|Aquaculteur",
    ],
}

ALL_JOB_PATTERNS = [
    pattern for sublist in JOB_DICTIONARY.values() for pattern in sublist
]


def extract_job_title_fallback(text: str, default: str = "Développeur") -> str:
    """Extrait le poste du CV avec recherche prioritaire dans l'en-tête."""
    if not text or not text.strip():
        return default

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_text = " ".join(lines[:15])

    for pattern in ALL_JOB_PATTERNS:
        match = re.search(pattern, header_text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    for pattern in ALL_JOB_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    for line in lines[:5]:
        if len(line) < 60 and not re.search(
            r"@|phone|tél|adresse|curriculum|cv|permis|français",
            line,
            re.IGNORECASE,
        ):
            return line

    return default


def analyze_cv_with_fallback(
    text: str,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> dict:
    """Analyse un CV via l'IA. Si l'IA échoue, utilise un parser regex local."""
    fallback_used = False
    try:
        response_text = call_ai_provider(
            """Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON en {target_lang} avec les clés suivantes :
            "nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier), "recommandations_metiers" (liste de 5 métiers suggérés), "metiers_alternatifs" (liste de 3 métiers radicalement différents utilisant les mêmes compétences transférables), "suggestions_amelioration" (liste de 3 à 5 conseils concrets pour améliorer l'impact de ce CV).

            LOGIQUE D'IDENTIFICATION DU MÉTIER :
            - Si le profil contient des métiers multiples (ex: "Consultant & Développeur"), NE les regroupe PAS.
            - Sélectionne le métier le plus porteur/pertinent pour une recherche d'emploi actuelle comme "metier" principal.
            - Place le second métier (ou les métiers connexes identifiés) en priorité absolue au début de la liste "recommandations_metiers".

            Texte du CV :
            {text}""",
            selected_model,
            is_json=True,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=groq_api_key,
            ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key,
        )
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, dict) and data.get("metier"):
                    return data
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception as e:
        logger.error(f"[Fallback] Erreur lors de l'analyse IA du CV : {e}")

    logger.info("[Fallback] Analyse IA indisponible. Utilisation du parser d'urgence regex/heuristique.")
    fallback_used = True
    metier = extract_job_title_fallback(text or "")

    first_lines = " ".join(
        [line.strip() for line in (text or "").splitlines() if line.strip()][:10]
    )
    keywords = []
    for token in re.split(r"[^A-Za-zÀ-ÖØ-öø-ÿ]+", first_lines):
        t = token.strip()
        if 3 <= len(t) <= 30:
            keywords.append(t)
    keywords = list(dict.fromkeys(keywords))[:12]

    return {
        "nom_complet": "",
        "contact": "",
        "metier": metier,
        "mots_cles": keywords,
        "resume": "Analyse en mode secours : métier détecté automatiquement à partir du CV.",
        "annees_experience": 0,
        "recommandations_metiers": [metier],
        "metiers_alternatifs": [],
        "suggestions_amelioration": [
            "Passez votre souris sur une offre pour générer une lettre de motivation personnalisée.",
            "Utilisez les filtres pour affiner vos sources et votre type de contrat.",
            "Téléversez un CV plus complet pour obtenir une analyse plus précise.",
        ],
        "is_fallback": fallback_used,
    }


def analyze_cv(
    text: str,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[dict]:
    """Analyse un CV via l'IA et retourne un dict structuré."""
    result = analyze_cv_with_fallback(
        text=text,
        target_lang=target_lang,
        selected_model=selected_model,
        gemini_api_key=gemini_api_key,
        xai_api_key=xai_api_key,
        groq_api_key=groq_api_key,
        ollama_url=ollama_url,
        custom_gemini_key=custom_gemini_key,
    )
    if not result:
        return None
    return result if not result.get("is_fallback") else result


def generate_cover_letter(
    cv_data: dict,
    job_title: str,
    company: str,
    job_description: str = "",
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[str]:
    """Génère une lettre de motivation personnalisée via l'IA."""
    if not cv_data:
        return None

    prompt = f"""
    Tu es un expert en recrutement. Rédige une lettre de motivation percutante, professionnelle et personnalisée en {target_lang}.
    
    INFORMATIONS DU CANDIDAT :
    - Nom : {cv_data.get('nom_complet')}
    - Contact : {cv_data.get('contact')}
    - Métier : {cv_data.get('metier')}
    - Compétences : {', '.join(cv_data.get('mots_cles', []))}
    - Expérience : {cv_data.get('annees_experience')} ans
    - Résumé : {cv_data.get('resume')}

    INFORMATIONS DU POSTE :
    - Titre : {job_title}
    - Entreprise : {company}
    - Description (si dispo) : {job_description}

    La lettre doit être structurée (Vous/Moi/Nous), montrer une réelle adéquation entre le profil et le poste, et rester concise.
    Utilise les informations de contact pour l'en-tête et signe la lettre avec le nom du candidat. Réponds uniquement par le texte de la lettre, sans commentaires additionnels.
    """
    try:
        return call_ai_provider(
            prompt, selected_model, is_json=False,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
    except Exception:
        return None


def rank_jobs_with_ai(
    cv_data: dict,
    jobs: List[dict],
    filters: dict,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> List[dict]:
    """Utilise l'IA pour classer les offres par pertinence par rapport au CV."""
    if not jobs or not cv_data:
        return jobs

    limit_tri = 20
    jobs_to_rank = jobs[:limit_tri]
    job_list_text = "\n".join([f"{i} | {j['title']} @ {j['company']}" for i, j in enumerate(jobs_to_rank)])

    prompt = f"""
    Tu es un expert en recrutement. Évalue la compatibilité (0 à 100%) entre le profil du candidat et les offres d'emploi suivantes.
    
    FILTRES CRITIQUES :
    - Type de contrat recherché : {filters.get('contrat')}
    - Télétravail : {'Oui' if filters.get('remote') else 'Non spécifié'}

    PROFIL CANDIDAT : {cv_data.get('metier')} ({cv_data.get('annees_experience')} ans d'exp). Compétences clés: {', '.join(cv_data.get('mots_cles', []))}
    
    LISTE DES OFFRES (format "index | titre @ entreprise") :
    {job_list_text}

    INSTRUCTIONS :
    Retourne UNIQUEMENT un objet JSON avec une clé "ranking" contenant une liste d'objets : 
    {{"ranking": [{{"id": index_numérique, "score": score_entier_0_a_100}}]}}
    L'ID doit être uniquement le numéro d'index fourni.
    """
    try:
        response_text = call_ai_provider(
            prompt, selected_model, is_json=True,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
        if not response_text:
            return jobs

        ranking_data = json.loads(response_text).get("ranking", [])
        ranked_list = []
        ranked_indices = []

        for item in ranking_data:
            try:
                idx_raw = item.get("id")
                score_raw = item.get("score")
                if isinstance(idx_raw, str):
                    idx_match = re.search(r'\d+', idx_raw)
                    if idx_match:
                        idx_raw = idx_match.group()
                if idx_raw is not None:
                    idx = int(idx_raw)
                    score = int(score_raw) if score_raw is not None else 0
                    if idx < len(jobs_to_rank):
                        job = {**jobs_to_rank[idx], "match_score": score}
                        ranked_list.append(job)
                        ranked_indices.append(idx)
            except (ValueError, TypeError):
                continue

        for i in range(len(jobs_to_rank)):
            if i not in ranked_indices:
                ranked_list.append(jobs_to_rank[i])

        if len(jobs) > limit_tri:
            ranked_list.extend(jobs[limit_tri:])

        return ranked_list
    except Exception as e:
        logger.error(f"Erreur tri IA: {e}")
        return jobs


def estimate_workload(
    mission_description: str,
    mission_title: str = "",
    cv_data: Optional[dict] = None,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[dict]:
    """Estime la charge de travail d'une mission freelance via l'IA."""
    
    # Build context about the candidate if available
    candidate_context = ""
    if cv_data:
        candidate_context = f"""
        PROFIL DU CANDIDAT :
        - Métier : {cv_data.get('metier', 'Non spécifié')}
        - Années d'expérience : {cv_data.get('annees_experience', 'Non spécifié')}
        - Compétences clés : {', '.join(cv_data.get('mots_cles', []))}
        """
    
    prompt = f"""
    Tu es un expert en estimation de projets freelance. Analyse cette mission et estime la charge de travail.
    
    TITRE DE LA MISSION : {mission_title}
    DESCRIPTION DE LA MISSION :
    {mission_description}
    
    {candidate_context}
    
    INSTRUCTIONS :
    Retourne UNIQUEMENT un objet JSON avec les clés suivantes :
    {{
        "estimated_hours": nombre entier d'heures estimées (arrondi à la dizaine la plus proche),
        "complexity_level": "low", "medium", "high", ou "very_high",
        "complexity_description": brève description du niveau de complexité (1-2 phrases),
        "key_tasks": liste de 3-5 tâches principales pour cette mission,
        "recommended_duration": durée recommandée en jours ou semaines
    }}
    
    Pour estimated_hours :
    - Faible complexité : 8-40 heures
    - Complexité moyenne : 40-80 heures  
    - Haute complexité : 80-160 heures
    - Très haute complexité : 160+ heures
    """
    
    try:
        response_text = call_ai_provider(
            prompt, selected_model, is_json=True,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
        if not response_text:
            return None
            
        return json.loads(response_text)
    except json.JSONDecodeError as je:
        logger.error(f"JSONDecodeError in workload estimation: {je}")
        if response_text:
            logger.error(f"Response text: {response_text}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'estimation de la charge de travail: {e}")
        return None