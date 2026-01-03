import streamlit as st
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
import streamlit.components.v1 as components
import sympy

# 1. CONFIGURATION
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ Clé API manquante ! Vérifie ton fichier .env")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. FONCTIONS UTILITAIRES (Parser Maison + HTML)
# ------------------------------------------------------------------

def parser_format_maison(texte_brut):
    """
    Transforme le texte brut de l'IA en dictionnaire structuré.
    Plus de JSON = Plus de bugs de backslashs !
    """
    data = {"titre": "Fiche d'exercices", "exercices": []}
    
    # On découpe par blocs
    blocs = texte_brut.split("===NOUVEL_EXERCICE===")
    
    # Le premier bloc contient souvent le titre
    if len(blocs) > 0:
        titre_match = re.search(r"TITRE_FICHE:\s*(.*)", blocs[0])
        if titre_match:
            data["titre"] = titre_match.group(1).strip()

    # On analyse les exercices (à partir du bloc 1 car le 0 est l'intro/titre)
    for bloc in blocs[1:]:
        exo = {
            "question": "",
            "reponse": "",
            "correction_detaillee": "",
            "difficulte": 1
        }
        
        # Extraction avec des balises simples
        q_match = re.search(r"QUESTION:\s*(.*?)\s*REPONSE:", bloc, re.DOTALL)
        r_match = re.search(r"REPONSE:\s*(.*?)\s*DETAIL:", bloc, re.DOTALL)
        d_match = re.search(r"DETAIL:\s*(.*?)\s*DIFFICULTE:", bloc, re.DOTALL)
        diff_match = re.search(r"DIFFICULTE:\s*(\d)", bloc)
        
        if q_match: exo["question"] = q_match.group(1).strip()
        if r_match: exo["reponse"] = r_match.group(1).strip()
        if d_match: exo["correction_detaillee"] = d_match.group(1).strip()
        if diff_match: exo["difficulte"] = int(diff_match.group(1))
        
        data["exercices"].append(exo)
        
    return data

def generer_html_fiche(titre, exercices):
    """Génère le HTML final avec MathJax"""
    exercices_html = ""
    for i, exo in enumerate(exercices, 1):
        # Conversion sauts de ligne en HTML
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
            processEscapes: true
        }},
        svg: {{ fontCache: 'global' }}
    }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f9; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; }}
        h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 20px; }}
        .exercice {{ border: 1px solid #ddd; padding: 20px; margin-bottom: 30px; border-radius: 8px; background: white; }}
        .exercice-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; margin-bottom: 15px; }}
        .reponse {{ background: #e6fffa; border-left: 4px solid #38b2ac; padding: 10px; margin: 10px 0; }}
        .detail {{ background: #fffbf0; border: 1px solid #fce588; padding: 10px; }}
        @media print {{
            .no-print {{ display: none; }}
            details {{ display: block; }}
            summary {{ display: none; }}
        }}
        .btn-print {{ display: block; width: 100%; padding: 10px; background: #28a745; color: white; text-align: center; cursor: pointer; border-radius: 5px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="no-print btn-print" onclick="window.print()">🖨️ Imprimer en PDF</div>
        <h1>📚 {titre}</h1>
        {exercices_html}
    </div>
</body>
</html>
    """

# Fonctions Outils pour le Tuteur
def outil_calcul_symbolique(expression, operation, variable="x"):
    try:
        expression = expression.replace("^", "**").replace(r"\times", "*")
        x = sympy.symbols(variable)
        expr = sympy.sympify(expression)
        if operation == "derive": res = sympy.diff(expr, x)
        elif operation == "integre": res = sympy.integrate(expr, x)
        elif operation == "simplifie": res = sympy.simplify(expr)
        elif operation == "resous": res = sympy.solve(expr, x)
        else: return "Opération inconnue"
        return f"Résultat : ${sympy.latex(res)}$"
    except Exception as e:
        return f"Erreur : {str(e)}"

# 3. INTERFACE PRINCIPALE
# ------------------------------------------------------------------
st.title("🎓 Plateforme Maths IA (Version Stable)")

tab1, tab2 = st.tabs(["💬 Tuteur (Assistant)", "📝 Générateur de Fiches"])

# --- ONGLET 1 : TUTEUR ---
with tab1:
    st.write("### 🤖 Assistant Mathématique")
    st.write("Pose tes questions, je peux résoudre des équations et t'expliquer les cours.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": "Tu es un prof de maths bienveillant."}]

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("Ex: Explique-moi le théorème de Pythagore..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            )
            reply = response.choices[0].message.content
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

# --- ONGLET 2 : GÉNÉRATEUR ---
with tab2:
    st.header("📄 Générateur de Fiches (Zéro Bug JSON)")
    
    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet", "Fonctions affines")
        niveau = st.selectbox("Niveau", ["Collège", "Lycée", "Supérieur"])
    with c2:
        nb = st.slider("Nombre d'exos", 1, 5, 2)
        diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5], value=3)

    if st.button("🚀 Générer la fiche", type="primary"):
        with st.spinner("Création de la fiche..."):
            try:
                # PROMPT "FORMAT MAISON" (Plus de JSON, plus de problèmes)
                prompt_systeme = """Tu es un professeur.
                Génère une fiche d'exercices.
                
                IMPORTANT : N'utilise PAS de format JSON. Utilise EXACTEMENT ce format texte :
                
                TITRE_FICHE: Le titre ici
                
                ===NOUVEL_EXERCICE===
                QUESTION: Énoncé en LaTeX (ex: $x^2$)
                REPONSE: La réponse
                DETAIL: Les étapes
                DIFFICULTE: 3
                
                ===NOUVEL_EXERCICE===
                QUESTION: ...
                (et ainsi de suite)
                """
                
                user_content = f"Sujet: {sujet}, Niveau: {niveau}, Difficulté: {diff}, {nb} exercices."

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": prompt_systeme},
                        {"role": "user", "content": user_content}
                    ]
                )
                
                texte_ia = response.choices[0].message.content
                
                # Parsing manuel (Indestructible)
                data = parser_format_maison(texte_ia)
                
                # Génération HTML
                html = generer_html_fiche(data['titre'], data['exercices'])
                
                st.success(f"✅ Fiche prête : {data['titre']}")
                st.components.v1.html(html, height=600, scrolling=True)
                st.download_button("📥 Télécharger la Fiche (HTML)", html, "fiche.html", "text/html")
                
            except Exception as e:
                st.error(f"Une erreur est survenue : {e}")