import streamlit as st
import os
import json
import sympy
import re
from dotenv import load_dotenv
from openai import OpenAI
import streamlit.components.v1 as components

# CONFIGURATION
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

if not os.getenv("OPENAI_API_KEY"):
    st.error("Clé API manquante !")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------
# ⭐ LA FONCTION DE RÉPARATION (VERSION AGRESSIVE)
# ---------------------------------------------------------
def reparer_json_latex(json_str):
    """
    Répare le JSON. Convertit tout en LaTeX compatible JSON (double backslash).
    Convertit aussi \( ... \) en $ ... $ pour un affichage parfait.
    """
    if not json_str: return ""

    txt = json_str

    # 1. Remplacement des parenthèses LaTeX \( et \) par des $
    # (Cela règle le problème d'affichage du PDF où on voyait \(v_n\))
    txt = txt.replace(r'\(', '$').replace(r'\)', '$')
    txt = txt.replace(r'\[', '$$').replace(r'\]', '$$')

    # 2. Liste des mots-clés mathématiques à réparer
    # On force le double backslash pour TOUS ces mots, qu'ils aient déjà un \ ou non.
    keywords = [
        'times', 'frac', 'sqrt', 'vec', 'text', 'cdot', 'infty', 
        'approx', 'neq', 'geq', 'leq', 'begin', 'end', 'pi', 
        'alpha', 'beta', 'gamma', 'Delta', 'mathbb', 'limits', 'sum', 'int'
    ]

    for word in keywords:
        # On remplace "word" (précédé ou non de \) par "\\word"
        # Exemple : "imes" -> "\\times"  ET  "\times" -> "\\times"
        pattern = re.compile(r'\\?' + word + r'\b') 
        txt = pattern.sub(r'\\\\' + word, txt)

    # 3. Réparation spécifique des accolades vecteurs/fractions
    # vec{ -> \\vec{
    txt = txt.replace(r'vec{', r'\\vec{').replace(r'\\\\vec{', r'\\vec{') 
    
    # 4. Nettoyage des sauts de ligne systèmes
    txt = txt.replace(r'\\', r'\\\\') 

    # 5. Nettoyage final des triples backslashs accidentels
    txt = txt.replace(r'\\\times', r'\\times')
    txt = txt.replace(r'\\\frac', r'\\frac')

    return txt
# ---------------------------------------------------------


# FONCTION POUR GÉNÉRER LE HTML
def generer_html_fiche(titre, exercices):
    exercices_html = ""
    for i, exo in enumerate(exercices, 1):
        # On s'assure que les sauts de ligne texte deviennent des <br>
        q = exo['question'].replace('\n', '<br>')
        r = exo['reponse']
        d = exo['correction_detaillee'].replace('\n', '<br>')
        
        exercices_html += f"""
        <div class="exercice">
            <div class="exercice-header">
                <h2>📝 Exercice {i}</h2>
                <span class="difficulte">{'⭐' * exo['difficulte']}</span>
            </div>
            <div class="question">{q}</div>
            <details class="correction">
                <summary>📖 Voir la correction</summary>
                <div class="reponse"><strong>Réponse :</strong> {r}</div>
                <div class="detail"><strong>Détail :</strong><br>{d}</div>
            </details>
        </div>
        """
    
    html_complete = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{titre}</title>
    <script>
    window.MathJax = {{
        tex: {{
            inlineMath: [['$', '$']],
            displayMath: [['$$', '$$']],
            processEscapes: true
        }},
        svg: {{ fontCache: 'global' }}
    }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f9; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 20px; }}
        .exercice {{ border: 1px solid #e1e4e8; padding: 20px; margin-bottom: 30px; border-radius: 8px; page-break-inside: avoid; }}
        .exercice-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; margin-bottom: 15px; }}
        .exercice-header h2 {{ color: #2980b9; font-size: 1.3em; margin: 0; }}
        .difficulte {{ color: #f1c40f; }}
        summary {{ cursor: pointer; color: #007bff; font-weight: bold; margin-top: 10px; }}
        .reponse {{ background: #e6fffa; border-left: 4px solid #38b2ac; padding: 10px; margin: 10px 0; }}
        .detail {{ background: #fffbf0; border: 1px solid #fce588; padding: 10px; }}
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; padding: 0; }}
            details {{ display: block; }}
            summary {{ display: none; }}
            .correction {{ display: block !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 {titre}</h1>
        {exercices_html}
    </div>
</body>
</html>
    """
    return html_complete

# --- INTERFACE STREAMLIT ---
st.title("🎓 Générateur de Fiches Maths (Version Finale)")

with st.sidebar:
    sujet = st.text_input("Sujet", "Intégrales")
    niveau = st.selectbox("Niveau", ["Terminale", "Bac+1", "Bac+2"])
    nb = st.slider("Nombre d'exos", 1, 5, 2)
    diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5], value=3)

if st.button("🚀 Générer la fiche"):
    with st.spinner("Génération..."):
        try:
            # Prompt Système : On force l'utilisation des $ pour simplifier la vie de MathJax
            sys_prompt = """Tu es un prof de maths. Génère un JSON strict.
            IMPORTANT : Utilise UNIQUEMENT des dollars $ pour les maths. N'utilise PAS \\( ou \\).
            Exemple : $x^2$ et non \\(x^2\\).
            Format : {"titre": "...", "exercices": [{"question": "...", "reponse": "...", "correction_detaillee": "...", "difficulte": 3}]}
            """

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Sujet: {sujet}, Niveau: {niveau}, Diff: {diff}, {nb} exos."}
                ],
                response_format={"type": "json_object"}
            )
            
            json_brut = response.choices[0].message.content
            
            # Réparation
            json_repare = reparer_json_latex(json_brut)
            data = json.loads(json_repare)
            
            # Génération HTML
            html = generer_html_fiche(data['titre'], data['exercices'])
            
            st.success("Fiche prête !")
            
            # Affichage et Téléchargement
            st.components.v1.html(html, height=800, scrolling=True)
            
            c1, c2 = st.columns(2)
            c1.download_button("📥 Télécharger HTML", html, "fiche.html", "text/html")
            c2.download_button("📄 JSON Debug", json_repare, "debug.json", "application/json")
            
        except Exception as e:
            st.error(f"Erreur : {e}")