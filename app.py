import streamlit as st
import os
import json
import sympy
import re
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# 1. CONFIGURATION
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

# ⭐ AJOUT : Configuration MathJax pour Streamlit
st.markdown("""
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
  }
};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
""", unsafe_allow_html=True)

if not os.getenv("OPENAI_API_KEY"):
    st.error("Clé API manquante ! Vérifie tes secrets Streamlit.")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. MODÈLES DE DONNÉES (PYDANTIC)
# ------------------------------------------------------------------
class ExerciceMaths(BaseModel):
    question: str = Field(description="L'énoncé. Utilise Markdown (**gras**) pour le texte et LaTeX ($...$) pour les maths.")
    reponse: str = Field(description="La réponse finale.")
    correction_detaillee: str = Field(description="Le raisonnement complet.")
    difficulte: int = Field(description="Niveau 1 à 5.")

class FicheTD(BaseModel):
    titre: str = Field(description="Titre de la fiche.")
    exercices: list[ExerciceMaths]

# 3. ⭐ FONCTION DE NETTOYAGE AMÉLIORÉE
# ------------------------------------------------------------------
def nettoyer_latex(text):
    """
    Corrige le formatage LaTeX pour l'affichage dans Streamlit.
    Gère les backslashs perdus et les délimiteurs manquants.
    """
    if not text:
        return ""
    
    # Étape 1 : Réparation des commandes LaTeX courantes (backslash perdu)
    corrections = {
        r'\\times': r'\\times',      # Déjà correct
        r'times': r'\\times',         # Manquant
        r'imes': r'\\times',          # Partiellement perdu
        r'\\frac': r'\\frac',
        r'frac': r'\\frac',
        r'\\vec': r'\\vec',
        r'vec': r'\\vec',
        r'\\sqrt': r'\\sqrt',
        r'sqrt': r'\\sqrt',
        r'\\mathbb': r'\\mathbb',
        r'mathbb': r'\\mathbb',
        r'\\begin': r'\\begin',
        r'begin': r'\\begin',
        r'\\end': r'\\end',
        r'end{': r'\\end{',
        r'\\text': r'\\text',
        r'text{': r'\\text{',
    }
    
    # Application des corrections (ordre important !)
    for pattern, replacement in corrections.items():
        # Éviter de doubler les backslashs déjà corrects
        if pattern.startswith('\\\\'):
            continue
        text = text.replace(pattern, replacement)
    
    # Étape 2 : Conversion des délimiteurs LaTeX
    # \[ ... \] → $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # \( ... \) → $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    # Étape 3 : Gestion des environments (cases, align, etc.)
    # Forcer les $$ autour des environments
    text = re.sub(
        r'(\\begin\{cases\}.*?\\end\{cases\})',
        r'$$\1$$',
        text,
        flags=re.DOTALL
    )
    
    # Étape 4 : Nettoyage des commandes de formatage PDF
    text = text.replace(r'\newline', '\n\n')
    text = text.replace(r'\\\\', '\n\n')  # Double backslash → saut de ligne
    
    # Conversion \textbf{} → **Markdown**
    text = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', text)
    text = re.sub(r'\\textit\{(.*?)\}', r'*\1*', text)
    
    # Étape 5 : Protection des formules isolées
    # Si une ligne contient du LaTeX sans délimiteurs, on les ajoute
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Détection de commandes LaTeX sans $ autour
        if re.search(r'\\(frac|sqrt|vec|sum|int|lim|mathbb)', line) and not re.search(r'\$', line):
            lines[i] = f'${line.strip()}$'
    
    text = '\n'.join(lines)
    
    return text


def outil_calcul_symbolique(expression, operation, variable="x"):
    try:
        # Petit nettoyage pré-calcul
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
        
        return f"Résultat (SymPy) : ${sympy.latex(res)}$"
    except Exception as e:
        return f"Erreur : {str(e)}"


tools_schema = [{
    "type": "function",
    "function": {
        "name": "calcul_maths",
        "description": "Calcul exact via Python.",
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

# 4. INTERFACE
# ------------------------------------------------------------------
st.title("🎓 Plateforme Maths IA")

tab1, tab2 = st.tabs(["💬 Tuteur", "📝 Générateur"])

with tab1:
    st.write("Pose ta question, je calcule avec Python.")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": "Tu es un assistant mathématique."}]

    for msg in st.session_state.messages:
        # Conversion forcée pour éviter les bugs d'objets
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.role
        
        if content and role != "system":  # Ne pas afficher le système
            with st.chat_message(role):
                st.markdown(nettoyer_latex(content), unsafe_allow_html=True)

    if prompt := st.chat_input("Ex: Primitive de x*ln(x)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            container = st.empty()
            # Appel API
            response = client.chat.completions.create(
                model="gpt-4o", messages=st.session_state.messages, tools=tools_schema
            )
            msg_obj = response.choices[0].message
            
            if msg_obj.tool_calls:
                st.session_state.messages.append(msg_obj)
                for tool in msg_obj.tool_calls:
                    if tool.function.name == "calcul_maths":
                        args = json.loads(tool.function.arguments)
                        with st.status(f"Calcul : {args['operation']}..."):
                            res = outil_calcul_symbolique(args["expression"], args["operation"])
                        st.session_state.messages.append({
                            "tool_call_id": tool.id, "role": "tool", "name": "calcul_maths", "content": res
                        })
                
                final = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                reply = final.choices[0].message.content
                container.markdown(nettoyer_latex(reply), unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                reply = msg_obj.content
                container.markdown(nettoyer_latex(reply), unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": reply})

with tab2:
    st.header("Générateur de Fiches")
    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet", "Intégrales")
        niveau = st.selectbox("Niveau", ["1ère", "Terminale", "Bac+1"])
    with c2:
        nb = st.slider("Nombre d'exos", 1, 5, 2)
        diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5])

    if st.button("🚀 Générer"):
        with st.spinner("Rédaction en cours..."):
            try:
                # ⭐ PROMPT SYSTÈME AMÉLIORÉ
                sys_prompt = """
                Tu es un professeur de mathématiques expert qui génère des exercices de qualité.
                
                RÈGLES DE FORMATAGE STRICTES :
                
                1. **Texte normal** : Utilise le Markdown standard
                   - **Gras** avec **texte**
                   - *Italique* avec *texte*
                   - Jamais de \\textbf{} ou \\textit{}
                
                2. **Formules mathématiques** : TOUTES les maths doivent être entre $ ou $$
                   - Inline : $x^2 + 1$
                   - Display : $$\\frac{a}{b}$$
                   - Systèmes : $$\\begin{cases} x = 1 \\\\ y = 2 \\end{cases}$$
                
                3. **Commandes LaTeX** : TOUJOURS doubler les backslashs dans le JSON
                   - Écris : \\\\times, \\\\frac{}{}, \\\\vec{u}, \\\\mathbb{R}
                   - Sinon le backslash sera perdu lors du parsing JSON
                
                4. **Structure** :
                   - Question claire avec contexte
                   - Réponse courte (résultat final)
                   - Correction détaillée avec étapes
                
                Exemple de bon formatage :
                "question": "Soit $f(x) = x^2 \\\\times \\\\ln(x)$. Calculer $f'(x)$.",
                "reponse": "$f'(x) = 2x\\\\ln(x) + x$",
                "correction_detaillee": "On utilise $(uv)' = u'v + uv'$ avec $u=x^2$ et $v=\\\\ln(x)$..."
                """
                
                completion = client.beta.chat.completions.parse(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"Crée une fiche sur : {sujet}. Niveau : {niveau}. Difficulté : {diff}/5. Nombre d'exercices : {nb}."}
                    ],
                    response_format=FicheTD,
                )

                fiche = completion.choices[0].message.parsed
                
                st.success(f"✅ Fiche générée : **{fiche.titre}**")
                st.markdown("---")
                
                for i, exo in enumerate(fiche.exercices, 1):
                    with st.container():
                        # Affichage du titre avec étoiles de difficulté
                        st.markdown(f"### Exercice {i} {'⭐' * exo.difficulte}")
                        
                        # Question
                        st.markdown(nettoyer_latex(exo.question), unsafe_allow_html=True)
                        
                        # Correction dans un expander
                        with st.expander("📖 Voir la correction"):
                            st.info(f"**Réponse :** {nettoyer_latex(exo.reponse)}")
                            st.markdown("**Détail :**")
                            st.markdown(nettoyer_latex(exo.correction_detaillee), unsafe_allow_html=True)
                        
                        st.markdown("---")

                # Bouton de téléchargement
                st.download_button(
                    "💾 Télécharger (JSON)",
                    fiche.model_dump_json(indent=2),
                    "fiche_maths.json",
                    "application/json"
                )

            except Exception as e:
                st.error(f"❌ Erreur lors de la génération : {e}")
                st.exception(e)  # Pour déboguer