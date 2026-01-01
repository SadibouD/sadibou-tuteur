import streamlit as st
import os
import json
import sympy
import re
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# 1. CONFIGURATION INITIALE
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA Pro", page_icon="🎓", layout="wide")

# Vérification de la clé API
if not os.getenv("OPENAI_API_KEY"):
    st.error(" Clé API manquante ! Vérifie ton fichier .env")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. DÉFINITION DES STRUCTURES DE DONNÉES (PYDANTIC)
# ------------------------------------------------------------------
class ExerciceMaths(BaseModel):
    question: str = Field(description="L'énoncé. Utilise le MARKDOWN pour le texte (gras, italique) et LaTeX entre $ pour les maths.")
    reponse: str = Field(description="La réponse finale courte.")
    correction_detaillee: str = Field(description="Le raisonnement complet. Utilise LaTeX pour les formules.")
    difficulte: int = Field(description="Niveau de difficulté de 1 à 5.")

class FicheTD(BaseModel):
    titre: str = Field(description="Le titre de la fiche de TD.")
    exercices: list[ExerciceMaths]

# 3. FONCTION DE NETTOYAGE CHIRURGICALE
# ------------------------------------------------------------------
def nettoyer_latex(text):
    """
    Répare les erreurs d'échappement JSON (imes, ext) et convertit
    le formatage LaTeX texte (\textbf) en Markdown (**).
    """
    if not text: return ""

    # --- ÉTAPE 1 : Réparation des "accidents" JSON (visible sur tes screens) ---
    # Le \t de \times est souvent interprété comme une tabulation
    text = text.replace('\t', ' ') 
    
    # Réparation spécifique des mots cassés par le manque de backslash
    # "imes" -> "\times" (mais on fait attention de ne pas casser le mot "cimes" par exemple)
    text = re.sub(r'(?<![a-zA-Z])imes(?![a-zA-Z])', r'\\times', text)
    text = re.sub(r'(?<![a-zA-Z])ext(?=\{)', r'\\text', text) # Répare "ext{...}" en "\text{...}"
    text = re.sub(r'(?<![a-zA-Z])vec(?=\{)', r'\\vec', text)   # Répare "vec{...}" en "\vec{...}"

    # --- ÉTAPE 2 : Conversion LaTeX Texte -> Markdown Streamlit ---
    # Remplacer \textbf{...} par **...**
    text = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', text)
    # Remplacer \textit{...} par *...*
    text = re.sub(r'\\textit\{(.*?)\}', r'*\1*', text)
    # Remplacer \newline par des vrais sauts de ligne
    text = text.replace(r'\newline', '\n\n').replace(r'\\', '\n\n')

    # --- ÉTAPE 3 : Conversion Maths Block \[ \] -> $$ $$ ---
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    # Nettoyage final des balises orphelines
    text = text.replace(r'\[', '$$').replace(r'\]', '$$')
    text = text.replace(r'\(', '$').replace(r'\)', '$')
    
    return text

def outil_calcul_symbolique(expression, operation, variable="x"):
    """Moteur de calcul SymPy"""
    try:
        # Nettoyage pré-calcul (ex: remplacer ^ par **)
        expression = expression.replace("^", "**")
        # On essaie d'enlever les $ si l'utilisateur en a mis
        expression = expression.replace("$", "").replace("\\", "")
        
        x = sympy.symbols(variable)
        expr = sympy.sympify(expression)
        
        if operation == "derive": res = sympy.diff(expr, x)
        elif operation == "integre": res = sympy.integrate(expr, x)
        elif operation == "simplifie": res = sympy.simplify(expr)
        elif operation == "resous": res = sympy.solve(expr, x)
        else: return "Opération inconnue"
        
        return f"Résultat exact (SymPy) : {sympy.latex(res)}"
    except Exception as e:
        return f"Erreur de calcul : {str(e)}"

# Définition outil pour l'onglet Chat
tools_schema = [{
    "type": "function",
    "function": {
        "name": "calcul_maths",
        "description": "Calcul mathématique exact via Python.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Expression mathématique (ex: x**2)"},
                "operation": {"type": "string", "enum": ["derive", "integre", "simplifie", "resous"]},
                "variable": {"type": "string", "default": "x"}
            },
            "required": ["expression", "operation"]
        }
    }
}]

# 4. INTERFACE GRAPHIQUE
# ------------------------------------------------------------------
st.title("🎓 Plateforme Maths ")

tab1, tab2 = st.tabs(["💬 Tuteur Interactif", "🏭 Usine à Exercices (JSON)"])

# ==========================================
# ONGLET 1 : CHATBOT
# ==========================================
with tab1:
    st.info("Pose ta question. Je calcule avec Python pour éviter les erreurs.")
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "Tu es un prof de maths expert. Utilise LaTeX entre $ pour les formules."}
        ]

    # Historique
    for msg in st.session_state.messages:
        if not isinstance(msg, dict): msg = msg.model_dump()
        if msg["role"] == "assistant" and msg.get("content"):
            with st.chat_message("assistant"): st.markdown(nettoyer_latex(msg["content"]))
        elif msg["role"] == "user":
            with st.chat_message("user"): st.markdown(nettoyer_latex(msg["content"]))
        elif msg["role"] == "tool":
            with st.expander(f"⚙️ Calcul ({msg.get('name')})"): st.markdown(nettoyer_latex(msg["content"]))

    # Input
    if prompt := st.chat_input("Ex: Calcule l'intégrale de x*cos(x)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(nettoyer_latex(prompt))

        with st.chat_message("assistant"):
            container = st.empty()
            # Appel 1
            response = client.chat.completions.create(
                model="gpt-4o", messages=st.session_state.messages, tools=tools_schema
            )
            msg_obj = response.choices[0].message
            
            # Gestion Outils
            if msg_obj.tool_calls:
                st.session_state.messages.append(msg_obj)
                for tool_call in msg_obj.tool_calls:
                    if tool_call.function.name == "calcul_maths":
                        args = json.loads(tool_call.function.arguments)
                        with st.status(f"Calcul : {args['operation']}...", expanded=True) as status:
                            res = outil_calcul_symbolique(args["expression"], args["operation"], args.get("variable", "x"))
                            status.update(label="Calcul terminé ✅", state="complete", expanded=False)
                        st.session_state.messages.append({
                            "tool_call_id": tool_call.id, "role": "tool", "name": "calcul_maths", "content": res
                        })
                
                # Appel 2 (Réponse finale)
                final = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                reply = final.choices[0].message.content
                container.markdown(nettoyer_latex(reply))
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                reply = msg_obj.content
                container.markdown(nettoyer_latex(reply))
                st.session_state.messages.append({"role": "assistant", "content": reply})

# ==========================================
# ONGLET 2 : GÉNÉRATEUR DE FICHES
# ==========================================
with tab2:
    st.header("Générateur de Fiches (Structured Outputs)")
    
    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet", "Probabilités conditionnelles")
        niveau = st.selectbox("Niveau", ["1e","Terminale", "Bac+1", "Bac+2"])
    with c2:
        nb_exos = st.slider("Nombre d'exos", 1, 5, 2)
        difficulte = st.select_slider("Difficulté", [1, 2, 3, 4, 5])

    if st.button("🚀 Générer la Fiche"):
        with st.spinner("Génération... (Cela prend quelques secondes)"):
            try:
                # PROMPT SYSTÈME AMÉLIORÉ
                system_prompt = """
                Tu es un professeur de mathématiques expert qui rédige des fiches d'exercices.
                RÈGLES DE FORMATAGE STRICTES :
                1. TEXTE : Utilise le MARKDOWN standard (**gras**, *italique*). N'utilise JAMAIS de commandes LaTeX pour le texte comme \\textbf{} ou \\newline.
                2. MATHS : Utilise LaTeX UNIQUEMENT pour les formules mathématiques, entourées de signes $.
                3. ÉCHAPPEMENT : Fais attention aux backslashs en JSON.
                """
                
                completion = client.beta.chat.completions.parse(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Génère {nb_exos} exercices sur : {sujet}. Niveau {niveau}. Difficulté {difficulte}/5."}
                    ],
                    response_format=FicheTD,
                )

                fiche = completion.choices[0].message.parsed
                
                st.divider()
                st.subheader(f"📄 {fiche.titre}")

                for i, exo in enumerate(fiche.exercices):
                    with st.container():
                        st.markdown(f"### Exercice {i+1} {'⭐'*exo.difficulte}")
                        
                        # Affichage Énoncé
                        st.markdown(nettoyer_latex(exo.question))
                        
                        # Correction
                        with st.expander("Correction"):
                            st.markdown("**Réponse :**")
                            st.info(nettoyer_latex(exo.reponse))
                            st.markdown("**Détail :**")
                            st.markdown(nettoyer_latex(exo.correction_detaillee))
                        st.markdown("---")

                # Téléchargement
                st.download_button(
                    label="💾 Télécharger JSON",
                    data=fiche.model_dump_json(indent=2),
                    file_name=f"fiche_{sujet.replace(' ','_')}.json",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"Erreur : {e}")