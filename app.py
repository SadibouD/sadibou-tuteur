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
    st.error("Clé API manquante !")
    st.stop()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. MODÈLES DE DONNÉES
# ------------------------------------------------------------------
class ExerciceMaths(BaseModel):
    question: str
    reponse: str
    correction_detaillee: str
    difficulte: int

class FicheTD(BaseModel):
    titre: str
    exercices: list[ExerciceMaths]

# 3. ⭐ RÉPARATION JSON (LA FONCTION MAGIQUE)
# ------------------------------------------------------------------
def reparer_json_latex(json_str):
    """
    Double les backslashs LaTeX dans le JSON avant parsing
    tout en préservant les échappements JSON légitimes
    """
    # Échappements JSON à préserver
    json_escapes = {
        r'\"': '§§QUOTE§§',
        r'\\': '§§BACKSLASH§§',
        r'\/': '§§SLASH§§',
        r'\b': '§§BACKSPACE§§',
        r'\f': '§§FORMFEED§§',
        r'\n': '§§NEWLINE§§',
        r'\r': '§§RETURN§§',
        r'\t': '§§TAB§§'
    }
    
    # Remplacer temporairement les vrais échappements JSON
    for escape, placeholder in json_escapes.items():
        json_str = json_str.replace(escape, placeholder)
    
    # Maintenant tous les \ restants sont du LaTeX cassé
    # On les double : \ → \\
    json_str = json_str.replace('\\', '\\\\')
    
    # Restaurer les vrais échappements JSON
    for escape, placeholder in json_escapes.items():
        json_str = json_str.replace(placeholder, escape)
    
    return json_str

# 4. ⭐ NETTOYAGE LATEX (POUR LE RENDU NATIF STREAMLIT)
# ------------------------------------------------------------------
def nettoyer_latex(text):
    """
    Prépare le LaTeX pour le rendu natif de Streamlit
    """
    if not text:
        return ""
    
    # 1. Supprimer les $ en trop ($$$ → $$)
    text = re.sub(r'\$\$\$+', '$$', text)
    text = re.sub(r'\$\$\s*\$\$', '', text)
    
    # 2. Forcer les environments dans des $$ si nécessaire
    def wrap_environment(match):
        content = match.group(0)
        # Si pas déjà dans $$, on entoure
        if not re.search(r'\$\$.*?' + re.escape(content), text):
            return f'$${content}$$'
        return content
    
    # Détecter les environments courants
    for env in ['cases', 'align', 'equation', 'matrix']:
        pattern = rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}'
        matches = re.finditer(pattern, text, flags=re.DOTALL)
        for match in matches:
            content = match.group(0)
            # Vérifier si déjà entouré
            start = match.start()
            end = match.end()
            before = text[max(0, start-2):start]
            after = text[end:min(len(text), end+2)]
            
            if before != '$$' and after != '$$':
                text = text[:start] + f'$${content}$$' + text[end:]
    
    # 3. Nettoyer les commandes de formatage PDF
    text = text.replace(r'\newline', '\n\n')
    
    # 4. Convertir LaTeX text en Markdown
    text = re.sub(r'\\textbf\{(.*?)\}', r'**\1**', text)
    text = re.sub(r'\\textit\{(.*?)\}', r'*\1*', text)
    
    # 5. Nettoyer les espaces autour des délimiteurs
    text = re.sub(r'\$\s+', '$', text)
    text = re.sub(r'\s+\$', '$', text)
    
    # 6. Normaliser les délimiteurs alternatifs
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    return text


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

# 5. INTERFACE
# ------------------------------------------------------------------
st.title("🎓 Plateforme Maths IA")

tab1, tab2 = st.tabs(["💬 Tuteur", "📝 Générateur"])

with tab1:
    st.write("Pose ta question de maths, je peux calculer avec Python.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": "Tu es un assistant mathématique expert."}
        ]

    for msg in st.session_state.messages:
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.role
        
        if content and role != "system":
            with st.chat_message(role):
                st.markdown(nettoyer_latex(content))

    if prompt := st.chat_input("Ex: Dérive ln(x²+1)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            container = st.empty()
            response = client.chat.completions.create(
                model="gpt-4o",
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
                    model="gpt-4o",
                    messages=st.session_state.messages
                )
                reply = final.choices[0].message.content
                container.markdown(nettoyer_latex(reply))
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                reply = msg_obj.content
                container.markdown(nettoyer_latex(reply))
                st.session_state.messages.append({"role": "assistant", "content": reply})

with tab2:
    st.header("📝 Générateur de Fiches TD")
    
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
                # ⭐ PROMPT OPTIMISÉ
                sys_prompt = """Tu es un professeur de mathématiques expérimenté.

RÈGLES DE FORMATAGE :
1. **Texte** : Utilise Markdown (**gras**, *italique*)
2. **Formules mathématiques** : Entoure TOUJOURS de $ ou $$
   - Inline : $f(x) = x^2 + 1$
   - Display : $$\\int_0^1 x^2 dx = \\frac{1}{3}$$
   
3. **Systèmes d'équations** : Structure exacte à respecter
   $$\\begin{cases}
   x = 1 + 2t \\\\
   y = 3 - t \\\\
   z = 5 + 4t
   \\end{cases}$$
   
IMPORTANT : 
- Double TOUJOURS les backslashs : \\\\
- Sépare les lignes des systèmes avec \\\\
- Utilise \\frac{}{} pour les fractions, jamais /

Structure JSON attendue :
{
  "titre": "...",
  "exercices": [
    {
      "question": "énoncé avec $maths$",
      "reponse": "réponse courte avec $résultat$",
      "correction_detaillee": "étapes détaillées",
      "difficulte": 1-5
    }
  ]
}"""
                
                # Appel API
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": 
                         f"Génère {nb} exercices sur '{sujet}' niveau {niveau}, difficulté {diff}/5. "
                         "Réponds UNIQUEMENT en JSON valide."
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                
                # ⭐ RÉCUPÉRATION + RÉPARATION JSON
                json_brut = response.choices[0].message.content
                json_repare = reparer_json_latex(json_brut)
                
                # Debug optionnel
                with st.expander("🔧 Debug JSON (optionnel)"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.caption("JSON brut (GPT-4)")
                        st.code(json_brut[:400] + "...", language="json")
                    with col_b:
                        st.caption("JSON réparé")
                        st.code(json_repare[:400] + "...", language="json")
                
                # Parsing
                data = json.loads(json_repare)
                fiche = FicheTD(**data)
                
                # Affichage
                st.success(f"✅ **{fiche.titre}**")
                st.markdown("---")
                
                for i, exo in enumerate(fiche.exercices, 1):
                    with st.container():
                        # En-tête exercice
                        cols = st.columns([3, 1])
                        with cols[0]:
                            st.markdown(f"### 📝 Exercice {i}")
                        with cols[1]:
                            st.markdown(f"{'⭐' * exo.difficulte}")
                        
                        # Énoncé
                        st.markdown(nettoyer_latex(exo.question))
                        
                        # Correction
                        with st.expander("📖 Voir la correction"):
                            st.info(f"**Réponse finale :** {nettoyer_latex(exo.reponse)}")
                            st.markdown("**Démonstration détaillée :**")
                            st.markdown(nettoyer_latex(exo.correction_detaillee))
                        
                        st.markdown("---")
                
                # Export
                col_export1, col_export2 = st.columns(2)
                with col_export1:
                    st.download_button(
                        "💾 Télécharger (JSON)",
                        fiche.model_dump_json(indent=2),
                        f"fiche_{sujet.replace(' ', '_')}.json",
                        "application/json"
                    )
                with col_export2:
                    # Export Markdown
                    md_content = f"# {fiche.titre}\n\n"
                    for i, exo in enumerate(fiche.exercices, 1):
                        md_content += f"## Exercice {i} ({'⭐' * exo.difficulte})\n\n"
                        md_content += f"{exo.question}\n\n"
                        md_content += f"**Réponse :** {exo.reponse}\n\n"
                        md_content += f"**Correction :**\n{exo.correction_detaillee}\n\n---\n\n"
                    
                    st.download_button(
                        "📄 Télécharger (Markdown)",
                        md_content,
                        f"fiche_{sujet.replace(' ', '_')}.md",
                        "text/markdown"
                    )

            except json.JSONDecodeError as e:
                st.error(f"❌ Erreur de parsing JSON : {e}")
                with st.expander("Voir le JSON problématique"):
                    st.code(json_repare)
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
                st.exception(e)

# Footer
st.markdown("---")
st.caption("💡 Astuce : Pour de meilleurs résultats, sois précis dans le sujet (ex: 'Dérivées de fonctions composées' plutôt que 'Dérivées')")