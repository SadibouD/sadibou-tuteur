import streamlit as st
import os
import json
import streamlit.components.v1 as components
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# 1. CONFIGURATION
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Maths Tutor IA", page_icon="🎓", layout="wide")

if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ Clé API manquante ! Vérifie ton fichier .env ou tes secrets Streamlit.")
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

# 3. GÉNÉRATEUR HTML (DESIGN + RÉPARATION § -> \)
# ------------------------------------------------------------------
def generer_html(fiche: FicheTD):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>{fiche.titre}</title>
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
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; background: white; color: #333; }}
            h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 20px; margin-bottom: 40px; }}
            
            .exo-container {{ border: 1px solid #ddd; border-radius: 8px; margin-bottom: 30px; overflow: hidden; page-break-inside: avoid; }}
            .exo-header {{ background: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; font-weight: bold; display: flex; justify-content: space-between; color: #2c3e50; }}
            .exo-content {{ padding: 20px; line-height: 1.6; font-size: 16px; }}
            
            .stars {{ color: #f1c40f; letter-spacing: 2px; }}
            
            details {{ margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px; }}
            summary {{ cursor: pointer; color: #007bff; font-weight: bold; outline: none; margin-bottom: 10px; }}
            summary:hover {{ text-decoration: underline; }}
            
            .correction {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba; }}
            
            /* Styles pour l'impression PDF */
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ padding: 0; background: white; }}
                .exo-container {{ border: none; border-bottom: 1px solid #ccc; border-radius: 0; }}
                details[open] summary {{ display: none; }}
            }}
            
            .btn-print {{ display: block; width: 100%; padding: 15px; background: #28a745; color: white; text-align: center; font-size: 18px; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 20px; font-weight: bold; }}
            .btn-print:hover {{ background: #218838; }}
        </style>
    </head>
    <body>
        <button class="btn-print no-print" onclick="window.print()">🖨️ Imprimer / Enregistrer en PDF</button>
        <h1>📄 {fiche.titre}</h1>
    """
    
    for i, exo in enumerate(fiche.exercices, 1):
        # --- RÉPARATION CRITIQUE ---
        # On remplace le leurre '§' par le vrai backslash '\' pour MathJax
        # On remplace les sauts de ligne Python '\n' par des balises HTML <br>
        q = exo.question.replace('§', '\\').replace("\n", "<br>")
        r = exo.reponse.replace('§', '\\')
        c = exo.correction_detaillee.replace('§', '\\').replace("\n", "<br>")
        
        html_content += f"""
        <div class="exo-container">
            <div class="exo-header">
                <span>Exercice {i}</span>
                <span class="stars">{'★' * exo.difficulte}</span>
            </div>
            <div class="exo-content">
                <div>{q}</div>
                
                <details class="no-print">
                    <summary>Voir la correction</summary>
                    <div class="correction">
                        <strong>Réponse :</strong> ${r}$<br><br>
                        <strong>Démonstration :</strong><br>{c}
                    </div>
                </details>
            </div>
        </div>
        """
        
    html_content += "</body></html>"
    return html_content

# 4. INTERFACE STREAMLIT
# ------------------------------------------------------------------
st.title("🏭 Générateur de Fiches (Mode Anti-Bug §)")
st.info("Ce générateur utilise une sécurité renforcée pour garantir un affichage parfait des maths.")

c1, c2 = st.columns(2)
with c1:
    sujet = st.text_input("Sujet", "Suites Arithmétiques")
    niveau = st.selectbox("Niveau", ["Terminale", "Bac+1", "Bac+2"])
with c2:
    nb = st.slider("Nombre d'exos", 1, 10, 2)
    diff = st.select_slider("Difficulté", [1, 2, 3, 4, 5])

if st.button("🚀 Générer la Fiche"):
    with st.spinner("L'IA rédige votre fiche (Sécurisation JSON en cours)..."):
        try:
            # PROMPT AVEC APPRENTISSAGE PAR L'EXEMPLE (FEW-SHOT)
            # On montre à l'IA exactement ce qu'on veut pour qu'elle imite le format.
            sys_prompt = """
            Tu es un professeur de mathématiques expert.
            Ton objectif est de générer une fiche d'exercices au format JSON strict.

            ⚠️ PROBLÈME TECHNIQUE :
            Le caractère backslash '\\' casse le format JSON. Tu ne dois JAMAIS l'utiliser.
            
            ✅ SOLUTION OBLIGATOIRE :
            Utilise le symbole '§' à la place de CHAQUE backslash '\\'.

            --- EXEMPLES À SUIVRE (MIMÉTISME) ---
            
            Exemple 1 (Vecteurs) :
            NE PAS ÉCRIRE : "Soit \\vec{u} le vecteur..."
            ÉCRIRE PLUTÔT : "Soit §vec{u} le vecteur..."

            Exemple 2 (Fractions et Limites) :
            NE PAS ÉCRIRE : "Calculer \\lim_{x \\to +\\infty} \\frac{1}{x}"
            ÉCRIRE PLUTÔT : "Calculer §lim_{x §to +§infty} §frac{1}{x}"

            Exemple 3 (Systèmes) :
            NE PAS ÉCRIRE : "\\begin{cases} ..."
            ÉCRIRE PLUTÔT : "§begin{cases} ..."

            -------------------------------------
            Génère le contenu demandé en respectant scrupuleusement cette règle du '§'.
            """
            
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Sujet: {sujet}. Niveau: {niveau}. Diff: {diff}/5. {nb} exercices."}
                ],
                response_format=FicheTD,
            )

            fiche = completion.choices[0].message.parsed
            
            # Génération du HTML (Nettoyage automatique § -> \)
            html_code = generer_html(fiche)
            
            st.success("✅ Fiche générée avec succès !")
            
            # Options de téléchargement
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    "📥 Télécharger la Fiche (HTML)",
                    data=html_code,
                    file_name="fiche_maths.html",
                    mime="text/html"
                )
            with col_b:
                st.download_button(
                    "💾 Sauvegarder JSON (Debug)",
                    data=fiche.model_dump_json(indent=2),
                    file_name="debug_data.json",
                    mime="application/json"
                )
            
            # Prévisualisation
            st.markdown("---")
            st.subheader("Aperçu Web")
            components.html(html_code, height=600, scrolling=True)

        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")