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

# Configuration MathJax optimale
st.markdown("""
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']],
    processEscapes: true,
    processEnvironments: true,
    packages: {'[+]': ['cases', 'amsmath']}
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

# 3. ⭐ FONCTION DE NETTOYAGE 
# ------------------------------------------------------------------
def nettoyer_latex(text):
    """
    Méthode hybride : Leurre § + nettoyage intelligent
    """
    if not text:
        return ""
    
    # ÉTAPE 1 : Remplacer le leurre § par \ si présent
    text = text.replace('§', '\\')
    
    # ÉTAPE 2 : Nettoyer les délimiteurs cassés
    # Cas 1 : $$$ → $$
    text = re.sub(r'\$\$\$+', '$$', text)
    # Cas 2 : $ $ → $
    text = re.sub(r'\$\s+\$', '$$', text)
    
    # ÉTAPE 3 : Forcer les environments dans des $$
    # Détecte \begin{cases}...\end{cases} et ajoute $$ si manquant
    def wrap_environment(match):
        content = match.group(0)
        # Si déjà entouré de $$, ne rien faire
        if content.startswith('$$') or content.endswith('$$'):
            return content
        return f'$${content}$$'
    
    text = re.sub(
        r'\\begin\{cases\}.*?\\end\{cases\}',
        wrap_environment,
        text,
        flags=re.DOTALL
    )
    
    # ÉTAPE 4 : Conversion des autres délimiteurs
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    # ÉTAPE 5 : Nettoyage des commandes de formatage
    text = text.replace(r'\newline', '\n\n')
    text = text.replace(r'\\\\', r'\\')  # Double backslash dans les cases
    
    # Conversion LaTeX → Markdown
    text = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', text)
    text = re.sub(r'\\textit\{(.*?)\}', r'*\1*', text)
    
    # ÉTAPE 6 : Correction des backslashs manquants (fallback)
    # Si malgré tout, certains mots sont cassés
    latex_commands = [
        'times', 'frac', 'sqrt', 'sum', 'int', 'lim',
        'alpha', 'beta', 'gamma', 'delta', 'lambda',
        'vec', 'overrightarrow', 'mathbb', 'mathcal',
        'text', 'begin', 'end'
    ]
    
    for cmd in latex_commands:
        # Remplace "cmd{" par "\cmd{" si pas déjà précédé de \
        text = re.sub(rf'(?<!\\){cmd}\{{', rf'\\{cmd}{{', text)
    
    # ÉTAPE 7 : Nettoyage final des espaces
    text = re.sub(r'\$\s+', '$', text)  # Enlever espaces après $
    text = re.sub(r'\s+\$', '$', text)  # Enlever espaces avant $
    
    return text


def outil_calcul_symbolique(expression, operation, variable="x"):
    try:
        expression = expression.replace("^", "**").replace(r"\times", "*").replace('§', '\\')
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
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.role
        
        if content and role != "system":
            with st.chat_message(role):
                st.markdown(nettoyer_latex(content), unsafe_allow_html=True)

    if prompt := st.chat_input("Ex: Primitive de x*ln(x)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            container = st.empty()
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
                # ⭐ PROMPT AVEC MÉTHODE DU LEURRE §
                sys_prompt = """
                Tu es un professeur de mathématiques expert.
                
                ⚠️ RÈGLE CRITIQUE POUR LE JSON :
                Le caractère backslash (\) est interdit dans les chaînes JSON car il casse le parsing.
                
                ✅ SOLUTION : Remplace TOUS les backslashs par le symbole §
                
                Exemples de conversion :
                - Au lieu de \\times → écris §times
                - Au lieu de \\frac{a}{b} → écris §frac{a}{b}
                - Au lieu de \\vec{u} → écris §vec{u}
                - Au lieu de \\begin{cases} → écris §begin{cases}
                - Au lieu de \\mathbb{R} → écris §mathbb{R}
                - Au lieu de x \\\\ y → écris x §§ y
                
                STRUCTURE DES FORMULES :
                1. **Formules inline** : Entoure avec $ : $§frac{1}{2}$
                2. **Formules display** : Entoure avec $$ : $$§int x^2 dx$$
                3. **Systèmes d'équations** : 
                   $$§begin{cases}
                   x = 1 + 2t §§
                   y = 2 - t §§
                   z = 3 + 4t
                   §end{cases}$$
                
                FORMATAGE TEXTE :
                - **Gras** : **texte**
                - *Italique* : *texte*
                - Jamais de §textbf ou §textit
                
                IMPORTANT : N'utilise JAMAIS le backslash \\ dans ta réponse JSON.
                Utilise uniquement § à la place, même pour les doubles backslashs (§§).
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
                        st.markdown(f"### Exercice {i} {'⭐' * exo.difficulte}")
                        
                        # Débug : afficher le brut
                        with st.expander("🔍 Debug (voir le LaTeX brut)"):
                            st.code(exo.question, language="text")
                        
                        # Question nettoyée
                        st.markdown(nettoyer_latex(exo.question), unsafe_allow_html=True)
                        
                        # Correction
                        with st.expander("📖 Voir la correction"):
                            st.info(f"**Réponse :** {nettoyer_latex(exo.reponse)}")
                            st.markdown("**Détail :**")
                            st.markdown(nettoyer_latex(exo.correction_detaillee), unsafe_allow_html=True)
                        
                        st.markdown("---")

                st.download_button(
                    "💾 Télécharger (JSON)",
                    fiche.model_dump_json(indent=2),
                    "fiche_maths.json",
                    "application/json"
                )

            except Exception as e:
                st.error(f"❌ Erreur : {e}")
                st.exception(e)