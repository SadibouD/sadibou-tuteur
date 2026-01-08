import streamlit as st
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
import streamlit.components.v1 as components

# 1. CONFIGURATION 
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    # 2. Dans les Secrets Streamlit (Cloud)
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except:
        pass

# Vérification de la clé DeepSeek
if not api_key:
    st.error("❌ Clé API manquante !")
    st.stop()

# Configuration du client pour DeepSeek
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"  # Adresse officielle de l'API DeepSeek
)

# 2. PARSEUR TEXTE (ROBUSTE)
# ------------------------------------------------------------------
def parser_format_maison(texte_brut):
    """
    Découpe le texte de l'IA en exercices structurés.
    """
    data = {"titre": "Fiche de Mathématiques", "exercices": []}
    
    texte_brut = texte_brut.replace("```text", "").replace("```", "")
    
    # Titre
    titre_match = re.search(r"TITRE_FICHE\s*:\s*(.*)", texte_brut, re.IGNORECASE)
    if titre_match:
        data["titre"] = titre_match.group(1).strip()

    # Blocs
    blocs = re.split(r"===NOUVEL_EXERCICE===", texte_brut)
    
    for bloc in blocs:
        if not bloc.strip() or "TITRE_FICHE" in bloc: continue

        exo = {
            "question": "",
            "reponse": "",
            "correction_detaillee": "",
            "difficulte": 3
        }
        
        q_match = re.search(r"QUESTION\s*:\s*(.*?)\s*REPONSE\s*:", bloc, re.DOTALL | re.IGNORECASE)
        r_match = re.search(r"REPONSE\s*:\s*(.*?)\s*DETAIL\s*:", bloc, re.DOTALL | re.IGNORECASE)
        d_match = re.search(r"DETAIL\s*:\s*(.*?)\s*DIFFICULTE\s*:", bloc, re.DOTALL | re.IGNORECASE)
        diff_match = re.search(r"DIFFICULTE\s*:\s*(\d)", bloc, re.IGNORECASE)
        
        # Fallback détail
        if d_match:
            exo["correction_detaillee"] = d_match.group(1).strip()
        else:
            fallback = re.search(r"DETAIL\s*:\s*(.*)", bloc, re.DOTALL | re.IGNORECASE)
            if fallback:
                exo["correction_detaillee"] = fallback.group(1).strip()

        if q_match: exo["question"] = q_match.group(1).strip()
        if r_match: exo["reponse"] = r_match.group(1).strip()
        if diff_match: exo["difficulte"] = int(diff_match.group(1))
        
        if exo["question"]:
            data["exercices"].append(exo)
        
    return data

# 3. GÉNÉRATEUR HTML (OPTIMISÉ)
# ------------------------------------------------------------------
def generer_html_fiche(titre, exercices):
    exercices_html = ""
    for i, exo in enumerate(exercices, 1):
        q = exo['question'].replace('\n', '<br>')
        r = exo['reponse']
        d = exo['correction_detaillee'].replace('\n', '<br>')
        
        exercices_html += f"""
        <div class="exercice">
            <div class="exercice-header">
                <h2>📝 Exercice {i}</h2>
                <span class="difficulte">{'⭐' * exo['difficulte']}</span>
            </div>
            
            <div class="question">
                {q}
            </div>
            
            <details class="correction">
                <summary>📖 Voir la correction détaillée</summary>
                <div class="reponse"><strong>Réponse :</strong> {r}</div>
                <div class="detail">
                    <strong>Explications :</strong><br>
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
        body {{ font-family: 'Helvetica', 'Arial', sans-serif; background: #f4f6f9; padding: 40px; line-height: 1.6; color: #333; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 60px; border-radius: 2px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #000; border-bottom: 2px solid #000; padding-bottom: 20px; margin-bottom: 50px; text-transform: uppercase; letter-spacing: 2px; }}
        .exercice {{ margin-bottom: 40px; page-break-inside: avoid; border-bottom: 1px dashed #ccc; padding-bottom: 30px; }}
        .exercice:last-child {{ border-bottom: none; }}
        .exercice-header {{ display: flex; justify-content: space-between; margin-bottom: 15px; align-items: baseline; }}
        .exercice-header h2 {{ color: #2c3e50; font-size: 1.4em; margin: 0; text-decoration: underline; }}
        .question {{ font-size: 1.15em; margin-bottom: 20px; text-align: justify; }}
        .correction {{ margin-top: 20px; background: #f8f9fa; padding: 15px; border-left: 3px solid #2980b9; }}
        .reponse {{ font-weight: bold; margin-bottom: 10px; color: #27ae60; }}
        .detail {{ font-size: 0.95em; color: #555; }}
        
        .btn-print {{ 
            display: block; width: 100%; padding: 20px; 
            background: #4b6cb7; color: white; text-align: center; 
            font-size: 20px; font-weight: bold; border-radius: 8px; 
            cursor: pointer; margin-bottom: 40px; text-decoration: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }}
        .btn-print:hover {{ background: #3b5998; }}

        @media print {{
            body {{ background: white; padding: 0; margin: 0; }}
            .container {{ box-shadow: none; border: none; width: 100%; max-width: 100%; margin: 0; padding: 40px; }}
            .no-print {{ display: none !important; }}
            details {{ display: block !important; }}
            summary {{ display: none !important; }}
            .correction {{ display: block !important; border: 1px solid #eee; }}
            a {{ text-decoration: none; color: black; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="#" class="no-print btn-print" onclick="window.print()">📥 Télécharger / Imprimer en PDF</a>
        <h1>📚 {titre}</h1>
        {exercices_html}
        <div style="text-align: center; margin-top: 50px; color: #aaa; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 20px;">
            Généré par Maths Tutor IA (DeepSeek Power)
        </div>
    </div>
</body>
</html>
    """

# 4. INTERFACE PRINCIPALE
# ------------------------------------------------------------------
st.title("🎓 Plateforme Maths IA")

tab1, tab2 = st.tabs(["💬 Tuteur", "📝 Générateur (Exos & QCM)"])

# --- ONGLET 1 : ASSISTANT ---
with tab1:
    st.write("### 🤖 Tuteur Intelligent")
    st.caption("Propulsé par DeepSeek-V3. Idéal pour les explications complexes.")
    
    sys_prompt_assistant = """
    Tu es un professeur de mathématiques expert et pédagogue.
    1. Langue : Français uniquement. Ne laisse jamais de mots anglais (comme 'From', 'we have', 'assuming').
    2. LaTeX : Utilise uniquement des dollars $ pour les formules. Exemple: $x^2$. N'utilise JAMAIS \[ ou \(.
    3. Rigueur : Sois précis. Pour la géométrie 3D, privilégie les systèmes d'équations.
       - Une droite dans l'espace est l'intersection de deux plans.
       - Son équation cartésienne est TOUJOURS un SYSTÈME de deux équations.
       - Exemple : $\\begin{cases} x - 2y + z = 0 \\\\ 3x + y - 5 = 0 \\end{cases}$
       - NE DONNE PAS la forme symétrique (ex: (x-a)/u = ...) car elle est peu utilisée en France.
       - Dans le plan mets la sous forme ax + by + c = 0. 
    """

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": sys_prompt_assistant}]

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                clean = msg["content"].replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "$").replace(r"\)", "$")
                st.markdown(clean)

    if prompt := st.chat_input("Pose ta question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                # Utilisation de DeepSeek Chat (V3)
                res = client.chat.completions.create(
                    model="deepseek-chat", 
                    messages=st.session_state.messages,
                    temperature=0.4
                )
                raw_reply = res.choices[0].message.content
                clean_reply = raw_reply.replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "$").replace(r"\)", "$")
                
                st.markdown(clean_reply)
                st.session_state.messages.append({"role": "assistant", "content": raw_reply})
            except Exception as e:
                st.error(f"Erreur DeepSeek : {e}")

# --- ONGLET 2 : GÉNÉRATEUR ---
with tab2:
    st.header("📄 Générateur de Fiches")
    
    col1, col2 = st.columns(2)
    with col1:
        sujet = st.text_input("Sujet", "Fonctions exponentielles")
        niveau = st.selectbox("Niveau", ["6e","5e","4e","3e","2nde","1e","Terminale","Bac+1","Bac+2"])
    with col2:
        
        type_exo = st.radio("Format :", ["Quiz","Exercices classiques", "Problème"])
        
        if type_exo == "Problème":
            nb = st.slider("Nombre de Problèmes", 1, 2, 1)
            diff = 4
        else:
            nb = st.slider("Nombre de questions", 1, 10, 5)
            diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5], value=3)

    if st.button("🚀 Générer", type="primary"):
        with st.spinner("L'IA réfléchit..."):
            try:
                # Construction du Prompt intelligent selon le type
                consigne_structure = ""
                
                if type_exo == "Quiz":
                    consigne_structure = """
                    Génère un QCM (Questionnaire à Choix Multiples).
                    Pour chaque exercice :
                    - QUESTION : L'énoncé suivi obligatoirement de 4 choix clairs : A) ... B) ... C) ... D) ...
                    - REPONSE : Juste la lettre de la bonne réponse (ex: Réponse B).
                    - DETAIL : L'explication complète de pourquoi c'est la bonne réponse.
                    """
                elif type_exo == "Problème":
                    consigne_structure = """
                    Génère un PROBLÈME COMPLET avec PARFOIS du contexte.
                    Tu peux PARFOIS utiliser ce type de format: Partie A (Étude préliminaire), Partie B (Fonction principale), Partie C (Application).
                    """
                else:
                    consigne_structure = "Génère des exercices d'entraînement technique variés, pas de calculs triviaux."

                prompt_systeme = f"""
                Tu es un professeur agrégé de mathématiques en France. Tu rédiges un sujet pertinent.
                MISSION : Générer {nb} exercices sur "{sujet}" (Niveau {niveau}).
                
                EXIGENCES CRITIQUES :
                1. CONTEXTE : Les exercices ne doivent pas être abstraits. Ajoute du contexte sur certains exercices (modélisation, physique, économie) quand c'est possible.
                2. RIGUEUR : Utilise les notations françaises (ln, exp, vecteurs avec flèche).
                3. TABLEAUX : Si tu dois faire un tableau de variations ou de signes, utilise IMPÉRATIVEMENT du LaTeX avec l'environnement `array`.
                   Exemple tableau de signe :
                   $$
                   \\begin{{array}}{{c|ccccc}}
                   x & -\\infty & & 2 & & +\\infty \\\\ \\hline
                   f'(x) & & - & 0 & + &
                   \\end{{array}}
                   $$
                   Exemple variations (utilise \\nearrow et \\searrow) :
                   $$
                   \\begin{{array}}{{c|ccccc}}
                   x & -\\infty & & 2 & & +\\infty \\\\ \\hline
                   f'(x) & & - & 0 & + & \\\\ \\hline
                   f(x) & +\\infty & \\searrow & -3 & \\nearrow & +\\infty \\\\[0.5cm]
                   \\end{{array}}
                   $$
                4. COMPLEXITÉ : Évite les questions triviales. Pose des questions "Montrer que...", "Déduire que...".

                TITRE_FICHE: [Titre]
                
                ===NOUVEL_EXERCICE===
                QUESTION: [Énoncé complet en LaTeX $. Utilise des sous-questions 1.a, 1.b...]
                REPONSE: [Résultat]
                DETAIL: [Démonstration]
                DIFFICULTE: {diff}
                
                {consigne_structure}
                """
                
                response = client.chat.completions.create(
                    model="deepseek-chat", # Modèle DeepSeek V3
                    messages=[
                        {"role": "system", "content": prompt_systeme},
                        {"role": "user", "content": "Génère la fiche."}
                    ],
                    temperature=0.5
                )
                
                texte_ia = response.choices[0].message.content
                data = parser_format_maison(texte_ia)
                
                if not data["exercices"]:
                    st.error("L'IA n'a pas renvoyé le bon format. Réessaie.")
                    st.expander("Voir réponse brute").text(texte_ia)
                else:
                    html = generer_html_fiche(data['titre'], data['exercices'])
                    st.success(f"✅ Fiche générée avec succès ! ({len(data['exercices'])} exos)")
                    st.components.v1.html(html, height=800, scrolling=True)
                    st.download_button("📥 Télécharger ", html, "fiche.html", "text/html")
                
            except Exception as e:
                st.error(f"Erreur API : {e}")