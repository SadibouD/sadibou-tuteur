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

# 3. Fonction de Nettoyage
# ------------------------------------------------------------------
def nettoyer_latex(text):
    if not text: return ""

    # 1. Réparation des backslashs mangés par le JSON (Visible sur tes images)
    # On remplace "imes" par "\times", "ext{" par "\text{", etc.
    text = text.replace("imes", r"\times") 
    text = text.replace("ext{", r"\text{")
    text = text.replace("extVar", r"\text{Var}")
    text = text.replace("extE", r"\text{E}")
    text = text.replace("mathbb", r"\mathbb")
    text = text.replace("mathcal", r"\mathcal")
    text = text.replace("vec{", r"\vec{")
    text = text.replace("overrightarrow", r"\overrightarrow")

    # 2. Suppression des commandes PDF parasites (\newline, \textbf)
    text = text.replace(r"\newline", "\n\n") # Vrai saut de ligne
    text = text.replace(r"\\", "\n\n")       # Autre type de saut de ligne
    
    # Transformation \textbf{Texte} -> **Texte** (Markdown)
    text = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', text)
    text = re.sub(r'\\textit\{(.*?)\}', r'*\1*', text)

    # 3. Forcer les dollars pour les blocs mathématiques isolés
    # Si on trouve des commandes LaTeX complexes sans $, on ajoute les $
    # (C'est un peu "bourrin" mais ça sauve l'affichage)
    
    # Conversion \[ ... \] -> $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    text = text.replace(r'\[', '$$').replace(r'\]', '$$')
    text = text.replace(r'\(', '$').replace(r'\)', '$')

    return text

def outil_calcul_symbolique(expression, operation, variable="x"):
    try:
        # Petit nettoyage pré-calcul
        expression = expression.replace("^", "**").replace(r"\times", "*")
        x = sympy.symbols(variable)
        expr = sympy.sympify(expression)
        
        if operation == "derive": res = sympy.diff(expr, x)
        elif operation == "integre": res = sympy.integrate(expr, x)
        elif operation == "simplifie": res = sympy.simplify(expr)
        elif operation == "resous": res = sympy.solve(expr, x)
        else: return "Opération inconnue"
        
        return f"Résultat (SymPy) : {sympy.latex(res)}"
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

tab1, tab2 = st.tabs(["💬 Tuteur", "🏭 Générateur"])

with tab1:
    st.write("Pose ta question, je calcule avec Python.")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": "Tu es un assistant mathématique."}]

    for msg in st.session_state.messages:
        # Conversion forcée pour éviter les bugs d'objets
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.role
        
        if content:
            with st.chat_message(role):
                st.markdown(nettoyer_latex(content))

    if prompt := st.chat_input("Ex: Primitive de x*ln(x)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

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
                container.markdown(nettoyer_latex(reply))
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                reply = msg_obj.content
                container.markdown(nettoyer_latex(reply))
                st.session_state.messages.append({"role": "assistant", "content": reply})

with tab2:
    st.header("Générateur de Fiches")
    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet", "Intégrales")
        niveau = st.selectbox("Niveau", ["1e", "Terminale", "Bac+1"])
    with c2:
        nb = st.slider("Nombre d'exos", 1, 5, 2)
        diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5])

    if st.button("🚀 Générer"):
        with st.spinner("Rédaction en cours..."):
            try:
                # PROMPT SYSTÈME RENFORCÉ (Le secret est ici)
                sys_prompt = """
                Tu es un professeur expert.
                RÈGLES CRITIQUES DE FORMATAGE :
                1. INTERDIT d'utiliser \\newline, \\textbf, \\textit. Utilise le Markdown (**gras**).
                2. MATHS : Toutes les formules DOIVENT être entourées de $ (ex: $f(x)=x^2$).
                3. JSON : Tu dois DOUBLER les backslashs pour les commandes LaTeX.
                   - Écris \\\\times, \\\\mathbb{R}, \\\\vec{u}, \\\\frac{a}{b}.
                   - Si tu écris un seul backslash, le code plantera. Sois très vigilant.
                """
                
                completion = client.beta.chat.completions.parse(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"Sujet: {sujet}. Niveau: {niveau}. Difficulte: {diff}/5. {nb} exercices."}
                    ],
                    response_format=FicheTD,
                )

                fiche = completion.choices[0].message.parsed
                
                st.subheader(f"📄 {fiche.titre}")
                for i, exo in enumerate(fiche.exercices):
                    with st.container():
                        st.markdown(f"### Exo {i+1} {'⭐'*exo.difficulte}")
                        st.markdown(nettoyer_latex(exo.question))
                        with st.expander("Correction"):
                            st.info(nettoyer_latex(exo.reponse))
                            st.markdown(nettoyer_latex(exo.correction_detaillee))
                        st.markdown("---")

                st.download_button("💾 JSON", fiche.model_dump_json(indent=2), "fiche.json")

            except Exception as e:
                st.error(f"Erreur : {e}")