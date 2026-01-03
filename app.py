import streamlit as st
import os
import json
import sympy
import re
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

# FONCTION DE RÉPARATION JSON

def reparer_json_latex(json_str):
    """
    Répare le JSON cassé par les backslashs manquants.
    Remplace brutalement les erreurs connues (imes, frac, etc.) par la version correcte.
    """
    if not json_str: return ""

    # Liste des réparations : (Erreur visible -> Correction JSON avec double backslash)
    corrections = [
        (r'imes', r'\\\\times'),       # imes -> \\times
        (r'frac', r'\\\\frac'),        # frac -> \\frac
        (r'sqrt', r'\\\\sqrt'),        # sqrt -> \\sqrt
        (r'vec\{', r'\\\\vec{'),       # vec{ -> \\vec{
        (r'text\{', r'\\\\text{'),     # text{ -> \\text{
        (r'cdot', r'\\\\cdot'),
        (r'infty', r'\\\\infty'),
        (r'approx', r'\\\\approx'),
        (r'neq', r'\\\\neq'),
        (r'geq', r'\\\\geq'),
        (r'leq', r'\\\\leq'),
        (r'begin\{', r'\\\\begin{'),
        (r'end\{', r'\\\\end{'),
        (r'pi', r'\\\\pi'),
        (r'alpha', r'\\\\alpha'),
        (r'beta', r'\\\\beta'),
        (r'gamma', r'\\\\gamma'),
        (r'Delta', r'\\\\Delta'),
        (r'lambda', r'\\\\lambda'),
        (r'mathbb', r'\\\\mathbb'),
        (r'mathcal', r'\\\\mathcal'),
        # Réparation des sauts de ligne systèmes
        (r'\\\\', r'\\\\\\\\')         # Essayer de doubler les backslashs simples restants
    ]

    txt_fixed = json_str
    
    for erreur, correction in corrections:
        # On remplace si le mot clé n'est PAS déjà précédé d'un backslash
        # (Technique Regex "Negative Lookbehind")
        pattern = r'(?<!\\)' + erreur
        try:
            txt_fixed = re.sub(pattern, correction, txt_fixed)
        except Exception:
            pass
            
    return txt_fixed

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
    
    html_complete = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titre}</title>
    
    <!-- MathJax -->
    <script>
    window.MathJax = {{
        tex: {{
            inlineMath: [['$', '$']],
            displayMath: [['$$', '$$']],
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
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        
        h1 {{
            color: #667eea;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        
        .exercice {{
            background: #f8f9fa;
            border-left: 5px solid #667eea;
            padding: 25px;
            margin-bottom: 30px;
            border-radius: 10px;
            transition: transform 0.2s;
        }}
        
        .exercice:hover {{
            transform: translateX(5px);
        }}
        
        .exercice-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .exercice-header h2 {{
            color: #667eea;
            font-size: 1.5em;
        }}
        
        .difficulte {{
            font-size: 1.2em;
        }}
        
        .question {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 1.1em;
        }}
        
        .correction {{
            margin-top: 15px;
        }}
        
        summary {{
            background: #667eea;
            color: white;
            padding: 12px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.3s;
        }}
        
        summary:hover {{
            background: #5568d3;
        }}
        
        .reponse {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        
        .detail {{
            background: white;
            padding: 20px;
            margin-top: 15px;
            border-radius: 5px;
            line-height: 1.8;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            details {{
                display: block;
            }}
            
            summary {{
                display: none;
            }}
            
            .correction {{
                display: block !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 {titre}</h1>
        {exercices_html}
        
        <div style="text-align: center; margin-top: 40px; color: #666;">
            <p>Généré par Maths Tutor IA 🎓</p>
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
        
        if operation == "derive":
            res = sympy.diff(expr, x)
        elif operation == "integre":
            res = sympy.integrate(expr, x)
        elif operation == "simplifie":
            res = sympy.simplify(expr)
        elif operation == "resous":
            res = sympy.solve(expr, x)
        else:
            return "Opération inconnue"
        
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
    st.info("💡 Nouvelle approche : Génération directe en HTML avec rendu parfait !")
    
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
                # PROMPT AVEC ÉCHAPPEMENT FORCÉ
                sys_prompt = """Tu es un professeur de mathématiques qui génère des exercices EN HTML.

RÈGLES CRITIQUES :
1. Utilise le HTML simple avec des balises <p>, <strong>, <em>
2. Pour les maths, utilise LaTeX entre $ (inline) ou $ (display)

3. ⚠️ RÈGLE LA PLUS IMPORTANTE - BACKSLASHS :
   Dans le JSON, tu DOIS échapper tous les backslashs LaTeX.
   Écris TOUJOURS 4 backslashs pour en obtenir 2 :
   
   ❌ INTERDIT : "\\times" (sera cassé → "imes")
   ✅ CORRECT : "\\\\times" (donnera → "\\times")
   
   Exemples :
   - Multiplication : "3 \\\\times 7" (PAS "3 \\times 7")
   - Fraction : "\\\\frac{5}{12}" (PAS "\\frac{5}{12}")
   - Vecteur : "\\\\vec{u}" (PAS "\\vec{u}")
   - Système : "\\\\begin{cases} ... \\\\\\\\ ... \\\\end{cases}"

4. Pour les systèmes d'équations :
   $\\\\begin{cases}
   x = 1 + 2t \\\\\\\\
   y = 3 - t \\\\\\\\
   z = 5
   \\\\end{cases}$

5. Structure JSON :
{
  "titre": "Titre de la fiche",
  "exercices": [
    {
      "question": "<p>Énoncé avec $f(x) = x^2$ en HTML</p>",
      "reponse": "<p>$x = 5$</p>",
      "correction_detaillee": "<p>Étape 1: $3 \\\\times 7 = 21$</p>",
      "difficulte": 3
    }
  ]
}

⚠️ RAPPEL FINAL : Quadruple TOUS les backslashs dans le JSON !"""

                response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": 
                         f"Génère {nb} exercices sur '{sujet}' niveau {niveau}, difficulté {diff}/5."
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                
                # Parser le JSON
                json_brut = response.choices[0].message.content
                
                # ⭐ RÉPARATION AUTOMATIQUE DES BACKSLASHS CASSÉS
                json_repare = reparer_json_latex(json_brut)
                
                # Debug
                with st.expander("🔧 Debug - Réparation automatique"):
                    col_debug1, col_debug2 = st.columns(2)
                    with col_debug1:
                        st.caption("❌ JSON cassé par GPT-4")
                        # Montrer les problèmes en rouge
                        problemes = ['imes', 'rac{', 'vec{', 'egin{', 'nd{']
                        extrait = json_brut[:800]
                        for pb in problemes:
                            if pb in extrait:
                                st.error(f"Trouvé: `{pb}`")
                        st.code(extrait, language="json")
                    with col_debug2:
                        st.caption("✅ JSON réparé automatiquement")
                        st.code(json_repare[:800], language="json")
                
                data = json.loads(json_repare)
                
                # Générer le HTML
                html_content = generer_html_fiche(data['titre'], data['exercices'])
                
                # Afficher dans Streamlit
                st.success(f"✅ Fiche générée : **{data['titre']}**")
                
                # Prévisualisation
                st.components.v1.html(html_content, height=800, scrolling=True)
                
                # Boutons de téléchargement
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.download_button(
                        "💾 Télécharger HTML",
                        html_content,
                        f"fiche_{sujet.replace(' ', '_')}.html",
                        "text/html"
                    )
                
                with col_b:
                    st.download_button(
                        "📄 Télécharger JSON",
                        json.dumps(data, indent=2, ensure_ascii=False),
                        f"fiche_{sujet.replace(' ', '_')}.json",
                        "application/json"
                    )
                
                st.info("💡 Astuce : Ouvre le fichier HTML dans ton navigateur, puis Ctrl+P pour l'imprimer en PDF !")

            except Exception as e:
                st.error(f"❌ Erreur : {e}")
                st.exception(e)

st.markdown("---")
st.caption("🎓 Maths Tutor IA - Nouvelle version HTML | Ctrl+P sur le HTML = PDF parfait !")