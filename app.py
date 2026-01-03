import streamlit as st
import os
import json
import sympy
import re  # Indispensable pour la réparation
from dotenv import load_dotenv
from openai import OpenAI
import base64

# CONFIGURATION
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

if not os.getenv("OPENAI_API_KEY"):
    st.error("Clé API manquante !")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------
# ⭐ LA FONCTION DE RÉPARATION (Celle qui manquait !)
# ---------------------------------------------------------
def reparer_json_latex(json_str):
    """
    Répare le JSON cassé par les backslashs manquants.
    Remplace les 'imes', 'frac' et nettoie les erreurs courantes.
    """
    if not json_str: return ""

    # Liste des réparations (Erreur -> Correction)
    corrections = [
        (r'(?<!\\)imes', r'\\\\times'),       # imes -> \\times
        (r'(?<!\\)frac', r'\\\\frac'),        # frac -> \\frac
        (r'(?<!\\)sqrt', r'\\\\sqrt'),        # sqrt -> \\sqrt
        (r'(?<!\\)vec\{', r'\\\\vec{'),       # vec{ -> \\vec{
        (r'(?<!\\)text\{', r'\\\\text{'),     # text{ -> \\text{
        (r'(?<!\\)cdot', r'\\\\cdot'),
        (r'(?<!\\)infty', r'\\\\infty'),
        (r'(?<!\\)approx', r'\\\\approx'),
        (r'(?<!\\)neq', r'\\\\neq'),
        (r'(?<!\\)geq', r'\\\\geq'),
        (r'(?<!\\)leq', r'\\\\leq'),
        (r'(?<!\\)begin\{', r'\\\\begin{'),
        (r'(?<!\\)end\{', r'\\\\end{'),
        (r'(?<!\\)pi', r'\\\\pi'),
        (r'(?<!\\)alpha', r'\\\\alpha'),
        (r'(?<!\\)beta', r'\\\\beta'),
        (r'(?<!\\)gamma', r'\\\\gamma'),
        (r'(?<!\\)mathbb', r'\\\\mathbb'),
        # Nettoyage des underscores échappés par erreur (v\_n -> v_n)
        (r'\\_', '_'),
        # Réparation des sauts de ligne systèmes mal formés
        (r'\\\\', r'\\\\\\\\') 
    ]

    txt_fixed = json_str
    
    for pattern, replacement in corrections:
        try:
            txt_fixed = re.sub(pattern, replacement, txt_fixed)
        except Exception:
            pass
            
    return txt_fixed
# ---------------------------------------------------------


# FONCTION POUR GÉNÉRER LE HTML
def generer_html_fiche(titre, exercices):
    """Génère un HTML complet avec MathJax pour les exercices"""
    
    exercices_html = ""
    for i, exo in enumerate(exercices, 1):
        exercices_html += f"""
        <div class="exercice">
            <div class="exercice-header">
                <h2>📝 Exercice {i}</h2>
                <span class="difficulte">{'⭐' * exo['difficulte']}</span>
            </div>
            
            <div class="question">
                {exo['question']}
            </div>
            
            <details class="correction">
                <summary>📖 Voir la correction</summary>
                <div class="reponse">
                    <strong>Réponse finale :</strong> {exo['reponse']}
                </div>
                <div class="detail">
                    <strong>Démonstration détaillée :</strong><br>
                    {exo['correction_detaillee']}
                </div>
            </details>
        </div>
        """
    
    # Amélioration MathJax : Ajout du support pour \( ... \) et \[ ... \]
    html_complete = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titre}</title>
    
    <script>
    window.MathJax = {{
        tex: {{
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], 
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true,
            packages: {{'[+]': ['amsmath', 'amssymb']}}
        }},
        svg: {{
            fontCache: 'global'
        }}
    }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" async></script>
    
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #333; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 40px; border-bottom: 2px solid #3498db; padding-bottom: 20px; }}
        .exercice {{ background: #fff; border: 1px solid #e1e4e8; padding: 25px; margin-bottom: 30px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .exercice-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .exercice-header h2 {{ color: #2980b9; font-size: 1.5em; }}
        .difficulte {{ font-size: 1.2em; color: #f1c40f; }}
        .question {{ font-size: 1.1em; margin-bottom: 20px; }}
        summary {{ background: #f1f8ff; color: #0366d6; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; list-style: none; }}
        summary:hover {{ background: #dbedff; }}
        .reponse {{ background: #e6fffa; border-left: 4px solid #38b2ac; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .detail {{ background: #fffbf0; border: 1px solid #fce588; padding: 15px; margin-top: 15px; border-radius: 4px; }}
        
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; border: none; width: 100%; max-width: 100%; padding: 0; }}
            details {{ display: block; }}
            summary {{ display: none; }}
            .correction {{ display: block !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 {titre}</h1>
        {exercices_html}
        <div style="text-align: center; margin-top: 40px; color: #666; font-size: 0.9em;">
            Généré par Maths Tutor IA 🎓
        </div>
    </div>
</body>
</html>
    """
    return html_complete

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

tools_schema = [{
    "type": "function",
    "function": {
        "name": "calcul_maths",
        "description": "Calcul symbolique exact",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string"},
                "operation": {"type": "string", "enum": ["derive", "integre", "simplifie", "resous"]},
                "variable": {"type": "string", "default": "x"}
            },
            "required": ["expression", "operation"]
        }
    }
}]

# INTERFACE
st.title("🎓 Plateforme Maths IA")

tab1, tab2 = st.tabs(["💬 Tuteur", "📝 Générateur"])

# TAB 1 : TUTEUR
with tab1:
    st.write("Pose ta question de maths, je peux calculer avec Python.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": "Tu es un assistant mathématique expert. Utilise LaTeX entre $ pour les formules."}
        ]

    for msg in st.session_state.messages:
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.role
        
        if content and role != "system":
            with st.chat_message(role):
                st.markdown(content)

    if prompt := st.chat_input("Ex: Dérive ln(x²+1)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            container = st.empty()
            response = client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=st.session_state.messages,
                tools=tools_schema
            )
            msg_obj = response.choices[0].message
            
            if msg_obj.tool_calls:
                st.session_state.messages.append(msg_obj)
                for tool in msg_obj.tool_calls:
                    if tool.function.name == "calcul_maths":
                        args = json.loads(tool.function.arguments)
                        with st.status(f"⚙️ Calcul : {args['operation']}"):
                            res = outil_calcul_symbolique(
                                args["expression"],
                                args["operation"],
                                args.get("variable", "x")
                            )
                        st.session_state.messages.append({
                            "tool_call_id": tool.id,
                            "role": "tool",
                            "name": "calcul_maths",
                            "content": res
                        })
                
                final = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=st.session_state.messages
                )
                reply = final.choices[0].message.content
                container.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                reply = msg_obj.content
                container.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

# TAB 2 : GÉNÉRATEUR HTML
with tab2:
    st.header("📝 Générateur de Fiches (HTML)")
    st.info("💡 Version : Génération HTML + Réparation automatique")
    
    col1, col2 = st.columns(2)
    with col1:
        sujet = st.text_input("📚 Sujet", "Équations paramétriques")
        niveau = st.selectbox("🎯 Niveau", ["1ère", "Terminale", "Bac+1", "Bac+2"])
    with col2:
        nb = st.slider("🔢 Nombre d'exercices", 1, 5, 3)
        diff = st.select_slider("⭐ Difficulté", [1, 2, 3, 4, 5], value=3)

    if st.button("🚀 Générer la fiche", type="primary"):
        with st.spinner("✍️ Rédaction en cours..."):
            try:
                # PROMPT 
                sys_prompt = """Tu es un professeur de mathématiques.

RÈGLE CRITIQUE : DANS LE JSON, DOUBLE TOUS LES BACKSLASHS LATEX.
Exemple : écris "\\\\times" au lieu de "\\times".
Exemple : écris "\\\\frac" au lieu de "\\frac".

Structure JSON :
{
  "titre": "Titre",
  "exercices": [
    {
      "question": "Énoncé avec LaTeX entre $",
      "reponse": "Réponse",
      "correction_detaillee": "Détails",
      "difficulte": 3
    }
  ]
}"""

                response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"Génère {nb} exercices sur '{sujet}' niveau {niveau}, difficulté {diff}/5."}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # 1. Récupération brute
                json_brut = response.choices[0].message.content
                
                # 2. Réparation automatique (FONCTIONNE MAINTENANT)
                json_repare = reparer_json_latex(json_brut)
                
                # 3. Parsing
                data = json.loads(json_repare)
                
                # 4. Génération HTML
                html_content = generer_html_fiche(data['titre'], data['exercices'])
                
                # 5. Affichage
                st.success(f"✅ Fiche générée : **{data['titre']}**")
                
                # Debug (visible si besoin)
                with st.expander("🛠️ Voir les détails techniques"):
                    c1, c2 = st.columns(2)
                    c1.text_area("JSON Brut (IA)", json_brut, height=200)
                    c2.text_area("JSON Réparé (Python)", json_repare, height=200)

                st.components.v1.html(html_content, height=800, scrolling=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button("💾 Télécharger HTML", html_content, "fiche.html", "text/html")
                with col_b:
                    st.download_button("📄 Télécharger JSON", json_repare, "fiche.json", "application/json")
                
            except Exception as e:
                st.error(f"❌ Erreur : {e}")