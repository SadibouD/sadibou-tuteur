import streamlit as st
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import sympy

# 1. CONFIGURATION
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ Clé API manquante ! Vérifie ton fichier .env")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. FONCTIONS PARSING & HTML (Générateur)
# ------------------------------------------------------------------

def executer_code_figure(code_python):
    """
    Exécute du code Matplotlib généré par l'IA et renvoie l'image en base64.
    """
    try:
        # Création d'un contexte de figure propre
        plt.figure(figsize=(6, 4))
        
        # Environnement sécurisé limité
        local_env = {'plt': plt, 'np': np}
        
        # Exécution du code (Attention : exec() exécute le code tel quel)
        exec(code_python, {}, local_env)
        
        # Sauvegarde dans un buffer mémoire
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close()
        buf.seek(0)
        
        # Encodage en base64 pour le HTML
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return f'<img src="data:image/png;base64,{img_str}" style="max-width:100%; margin: 10px auto; display:block; border:1px solid #eee; border-radius:5px;">'
    except Exception as e:
        return f"<div style='color:red; font-size:0.8em;'>Erreur génération figure : {e}</div>"
    

# def parser_format_maison(texte_brut):
#     """
#     Découpe le texte généré par l'IA en exercices structurés.
#     """
#     data = {"titre": "Fiche de Mathématiques", "exercices": []}
    
#     # On nettoie un peu le texte
#     texte_brut = texte_brut.replace("```text", "").replace("```", "")
    
#     # 1. Récupération du titre
#     titre_match = re.search(r"TITRE_FICHE:\s*(.*)", texte_brut, re.IGNORECASE)
#     if titre_match:
#         data["titre"] = titre_match.group(1).strip()

#     # 2. Découpage des exercices via le séparateur
#     blocs = re.split(r"===NOUVEL_EXERCICE===", texte_brut)
    
#     for bloc in blocs:
#         if not bloc.strip() or "TITRE_FICHE" in bloc: continue 

#         exo = {
#             "question": "",
#             "reponse": "",
#             "correction_detaillee": "",
#             "difficulte": 3
#         }
        
#         q_match = re.search(r"QUESTION:\s*(.*?)\s*REPONSE:", bloc, re.DOTALL)
#         r_match = re.search(r"REPONSE:\s*(.*?)\s*DETAIL:", bloc, re.DOTALL)
#         d_match = re.search(r"DETAIL:\s*(.*?)\s*DIFFICULTE:", bloc, re.DOTALL)
#         diff_match = re.search(r"DIFFICULTE:\s*(\d)", bloc)
        
#         if d_match:
#             exo["correction_detaillee"] = d_match.group(1).strip()
#         else:
#             detail_fallback = re.search(r"DETAIL:\s*(.*)", bloc, re.DOTALL)
#             if detail_fallback:
#                 exo["correction_detaillee"] = detail_fallback.group(1).strip()

#         if q_match: exo["question"] = q_match.group(1).strip()
#         if r_match: exo["reponse"] = r_match.group(1).strip()
#         if diff_match: exo["difficulte"] = int(diff_match.group(1))
        
#         if exo["question"]:
#             data["exercices"].append(exo)
        
#     return data

def parser_format_maison(texte_brut):
    data = {"titre": "Fiche de Mathématiques", "exercices": []}
    
    # Récupération du titre
    titre_match = re.search(r"TITRE_FICHE\s*:\s*(.*)", texte_brut, re.IGNORECASE)
    if titre_match:
        data["titre"] = titre_match.group(1).strip()

    # Découpage des blocs
    blocs = re.split(r"===NOUVEL_EXERCICE===", texte_brut)
    
    for bloc in blocs:
        if not bloc.strip() or "TITRE_FICHE" in bloc: continue

        exo = {
            "question": "",
            "reponse": "",
            "correction_detaillee": "",
            "figure": None, # Nouveau champ
            "difficulte": 3
        }
        
        # Regex mises à jour pour capturer CODE_PYTHON (optionnel)
        q_match = re.search(r"QUESTION\s*:\s*(.*?)\s*REPONSE\s*:", bloc, re.DOTALL | re.IGNORECASE)
        r_match = re.search(r"REPONSE\s*:\s*(.*?)\s*DETAIL\s*:", bloc, re.DOTALL | re.IGNORECASE)
        
        # On cherche le détail, mais on s'arrête soit à CODE_PYTHON soit à DIFFICULTE
        d_match = re.search(r"DETAIL\s*:\s*(.*?)\s*(CODE_PYTHON|DIFFICULTE)", bloc, re.DOTALL | re.IGNORECASE)
        
        # Capture du code python s'il existe
        py_match = re.search(r"CODE_PYTHON\s*:\s*(.*?)\s*DIFFICULTE", bloc, re.DOTALL | re.IGNORECASE)
        
        diff_match = re.search(r"DIFFICULTE\s*:\s*(\d)", bloc, re.IGNORECASE)

        if q_match: exo["question"] = q_match.group(1).strip()
        if r_match: exo["reponse"] = r_match.group(1).strip()
        if d_match: exo["correction_detaillee"] = d_match.group(1).strip()
        
        # Si on a trouvé du code python, on génère l'image tout de suite
        if py_match:
            code = py_match.group(1).strip().replace("```python", "").replace("```", "")
            exo["figure"] = executer_code_figure(code)

        if diff_match: exo["difficulte"] = int(diff_match.group(1))
        
        if exo["question"]:
            data["exercices"].append(exo)
        
    return data

def generer_html_fiche(titre, exercices):
    exercices_html = ""
    for i, exo in enumerate(exercices, 1):
        q = exo['question'].replace('\n', '<br>')
        r = exo['reponse']
        #d = exo['correction_detaillee'].replace('\n', '<br>')
        d = exo['correction_detaillee'].replace('\n', '<br>')
    
        # Gestion de la figure
        html_figure = ""
        if exo.get("figure"):
            html_figure = f"<div class='figure-math'>{exo['figure']}</div>"
        
        exercices_html += f"""
        <div class="exercice">
            ... (header et question comme avant) ...
            <div class="question">{q}</div>
            
            {html_figure} <details class="correction">
                ...
        """
        
        exercices_html += f"""
        <div class="exercice">
            <div class="exercice-header">
                <h2>📝 Exercice {i}</h2>
                <span class="difficulte">{'⭐' * exo['difficulte']}</span>
            </div>
            <div class="question">{q}</div>
            <details class="correction">
                <summary>📖 Voir la correction détaillée</summary>
                <div class="reponse"><strong>Résultat :</strong> {r}</div>
                <div class="detail">
                    <strong>Démonstration étape par étape :</strong><br>
                    {d}
                </div>
            </details>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{titre}</title>
    <script>
    window.MathJax = {{
        tex: {{
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], 
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true,
            packages: {{'[+]': ['amsmath', 'amssymb', 'noerrors', 'noundefined']}}
        }},
        svg: {{ fontCache: 'global' }}
    }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f9; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 950px; margin: 0 auto; background: white; padding: 50px; border-radius: 15px; }}
        h1 {{ text-align: center; color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 20px; margin-bottom: 40px; }}
        .exercice {{ border: 1px solid #ddd; padding: 25px; margin-bottom: 40px; border-radius: 12px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .exercice-header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #f0f0f0; margin-bottom: 20px; padding-bottom: 10px; }}
        .question {{ font-size: 1.1em; color: #2c3e50; margin-bottom: 15px; }}
        .reponse {{ background: #e8f6f3; border-left: 5px solid #1abc9c; padding: 15px; margin: 15px 0; font-weight: bold; color: #16a085; }}
        .detail {{ background: #fffbf0; border: 1px solid #ffeeba; padding: 20px; margin-top: 10px; border-radius: 5px; color: #444; }}
        
        /* Bouton Impression */
        .btn-print {{ 
            display: block; width: 100%; padding: 15px; 
            background: #27ae60; color: white; text-align: center; 
            font-size: 18px; font-weight: bold; border-radius: 8px; 
            cursor: pointer; margin-bottom: 30px; 
            box-shadow: 0 4px 6px rgba(39, 174, 96, 0.3);
        }}
        .btn-print:hover {{ background: #219150; }}

        @media print {{
            .no-print {{ display: none; }}
            details {{ display: block !important; }}
            summary {{ display: none; }}
            .correction {{ display: block !important; }}
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; border: none; width: 100%; margin: 0; padding: 20px; }}
            .exercice {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="no-print btn-print" onclick="window.print()">🖨️ Imprimer / Sauvegarder en PDF</div>
        <h1>📚 {titre}</h1>
        {exercices_html}
        <div style="text-align: center; margin-top: 50px; color: #aaa; font-size: 0.9em;">Généré par Maths Tutor IA</div>
    </div>
</body>
</html>
    """

# 3. INTERFACE
# ------------------------------------------------------------------
st.title("🎓 Plateforme Maths IA (Version Finale)")

tab1, tab2 = st.tabs(["💬 Assistant", "📝 Générateur de Fiches"])

# --- ONGLET 1 : ASSISTANT (CORRIGÉ POUR L'AFFICHAGE) ---
with tab1:
    st.write("Pose tes questions...")
    

    sys_prompt_assistant = """
    Tu es un professeur de mathématiques français expert et pédagogue.
    
    RÈGLES ABSOLUES :
    1. LANGUE : Réponds STRICTEMENT en français. Ne laisse jamais de mots anglais (comme 'From', 'we have', 'assuming').
    2. FORMAT : Utilise UNIQUEMENT des dollars ($) pour les formules. Exemple: $x^2$. N'utilise JAMAIS \[ ou \(.
    3. MATHÉMATIQUES (3D) :
       - Une droite dans l'espace est l'intersection de deux plans.
       - Son équation cartésienne est TOUJOURS un SYSTÈME de deux équations.
       - Exemple : $\\begin{cases} x - 2y + z = 0 \\\\ 3x + y - 5 = 0 \\end{cases}$
       - NE DONNE PAS la forme symétrique (ex: (x-a)/u = ...) car elle est peu utilisée en France.
       - Dans le plan mets la sous forme ax + by + c = 0. 
    """
    
    # Initialisation de l'historique
    if "messages" not in st.session_state:
        st.session_state.messages = [{
                "role": "system", 
                "content": sys_prompt_assistant
        }]

    # Affichage des messages existants
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                # ON NETTOIE L'HISTORIQUE AUSSI
                content_clean = msg["content"].replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "$").replace(r"\)", "$")
                st.markdown(content_clean)

    # Nouvelle question
    if prompt := st.chat_input("Question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            # Appel API
            res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
            raw_reply = res.choices[0].message.content
            
            clean_reply = raw_reply.replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "$").replace(r"\)", "$")
            
            st.markdown(clean_reply)
            st.session_state.messages.append({"role": "assistant", "content": raw_reply})

# --- ONGLET 2 : GÉNÉRATEUR ---
with tab2:
    st.header("📄 Création de Sujets")
    
    col1, col2 = st.columns(2)
    with col1:
        sujet = st.text_input("Sujet", "Fonctions exponentielles")
        niveau = st.selectbox("Niveau", ["6e","5e","4e","3e","2nde","1e","Terminale","Bac+1","Bac+2"])
    with col2:
        type_exo = st.radio("Type de contenu :", ["Exercices d'entraînement (Courts)", "Problèmes complets (Longs)"])
        
        if "Problèmes" in type_exo:
            nb = st.slider("Nombre de Problèmes", 1, 3, 1)
            diff = 5
            st.caption("ℹ️ Les problèmes sont longs, l'IA prendra plus de temps.")
        else:
            nb = st.slider("Nombre d'exercices", 1, 6, 3)
            diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5], value=3)

    if st.button("🚀 Générer le sujet", type="primary"):
        with st.spinner("Rédaction approfondie en cours (cela peut prendre 15-20 secondes)..."):
            try:
                consigne_detail = ""
                if "Problèmes" in type_exo:
                    structure_demande = "Génère des PROBLÈMES COMPLETS avec plusieurs parties (Partie A, Partie B...). Pose des questions enchaînées (1.a, 1.b, 2...)."
                    niveau_detail = "EXTRÊME. Pour chaque question, rappelle le théorème utilisé, détaille le calcul intermédiaire, et justifie rigoureusement."
                else:
                    structure_demande = "Génère des exercices d'application variés."
                    niveau_detail = "ÉLEVÉ. Détaille bien les étapes de calcul."

                prompt_systeme = f"""
                Tu es un professeur de mathématiques universitaire expert et pédagogue.
                
                MISSION :
                {structure_demande}
                
                FORMAT DE SORTIE IMPÉRATIF (Texte brut, PAS de JSON) :
                
                TITRE_FICHE: [Titre du sujet]
                
                ===NOUVEL_EXERCICE===
                QUESTION:
                [Énoncé complet ici. Utilise LaTeX $...$ pour les maths. Saute des lignes pour aérer. Si c'est un problème, utilise "1)", "2)", "a)", "b)".]
                
                REPONSE:
                [Juste les résultats finaux succincts]
                
                DETAIL:
                [CORRECTION TRÈS DÉTAILLÉE ICI. C'est la partie la plus importante.
                 - Explique la démarche.
                 - Cite les propriétés utilisées (ex: "D'après le théorème de...").
                 - Affiche les étapes de calcul intermédiaires.
                 - Sois très didactique.]

                CODE_PYTHON:
                [OPTIONNEL : Si une figure est nécessaire (courbe, géométrie), écris ICI le code Python Matplotlib pour la tracer. Utilise 'plt.plot()', 'plt.title()', etc. NE FAIS PAS de plt.show().]
                
                DIFFICULTE: {diff}
                
                (Répète ===NOUVEL_EXERCICE=== pour chaque exo)
                """
                
                user_content = f"Sujet: {sujet}. Niveau: {niveau}. Type: {type_exo}. Quantité: {nb}. {niveau_detail}"

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": prompt_systeme},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.7 
                )
                
                texte_ia = response.choices[0].message.content
                data = parser_format_maison(texte_ia)
                
                if not data["exercices"]:
                    st.error("L'IA n'a pas respecté le format. Réessaie.")
                    st.expander("Voir le texte brut").text(texte_ia)
                else:
                    html = generer_html_fiche(data['titre'], data['exercices'])
                    st.success(f"✅ Sujet généré avec {len(data['exercices'])} exercices/problèmes !")
                    st.components.v1.html(html, height=700, scrolling=True)
                    st.download_button("📥 Télécharger la Fiche (PDF via Impression)", html, "fiche_maths.html", "text/html")
                
            except Exception as e:
                st.error(f"Erreur : {e}")