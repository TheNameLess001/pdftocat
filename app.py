import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import requests
import io
from PIL import Image
from streamlit_cropper import st_cropper
import base64

# --- CONFIGURATION DE L'API IMGBB ---
# Remplacez par votre clé API ImgBB (obtenue sur api.imgbb.com)
IMGBB_API_KEY = "VOTRE_CLE_API_IMGBB_ICI"

def upload_to_imgbb(image_bytes, api_key):
    """Envoie une image à ImgBB et retourne l'URL directe."""
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": api_key,
        "image": base64.b64encode(image_bytes).decode("utf-8")
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_key == 200:
            return response.json()["data"]["url"]
        else:
            st.error(f"Erreur ImgBB : {response.text}")
            return None
    except Exception as e:
        st.error(f"Erreur de connexion ImgBB : {e}")
        return None

def extract_pdf_pages_as_images(pdf_file):
    """Convertit chaque page du PDF en une image PIL."""
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    pages_images = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Haute résolution
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pages_images.append(img)
    return pages_images

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Extracteur Menu & Images", layout="wide")
st.title("🍣 Extracteur de Menu PDF vers CSV (avec Images)")

st.markdown("""
Cette application permet de :
1. Charger votre menu PDF.
2. Découper (cropper) visuellement l'image de chaque plat.
3. Héberger automatiquement l'image sur ImgBB.
4. Ajouter les infos texte manuellement ou via un fichier CSV de base.
5. Exporter le catalogue final avec les URLs des images.
""")

# Étape 1 : Upload du PDF
uploaded_pdf = st.file_uploader("Chargez le menu au format PDF", type="pdf")

if "menu_data" not in st.session_state:
    # On initialise un DataFrame vide (vous pourriez ici injecter le CSV généré précédemment)
    st.session_state.menu_data = pd.DataFrame(columns=["nom", "category", "prix", "description", "image_url"])

if uploaded_pdf is not None:
    st.success("PDF chargé avec succès !")
    
    # Extraire les images des pages
    if "pages_images" not in st.session_state:
        with st.spinner("Extraction des pages en cours..."):
            st.session_state.pages_images = extract_pdf_pages_as_images(uploaded_pdf)
    
    # Étape 2 : Sélection de la page et découpage de l'image
    st.header("1. Capture d'image du produit")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        page_index = st.selectbox("Sélectionnez la page du PDF", range(len(st.session_state.pages_images)))
        selected_page_image = st.session_state.pages_images[page_index]
        
        st.write("Dessinez un rectangle autour du plat que vous souhaitez extraire :")
        # Outil de découpage interactif
        cropped_img = st_cropper(selected_page_image, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
        
    with col2:
        st.write("Aperçu de l'image découpée :")
        _ = cropped_img.thumbnail((300, 300))
        st.image(cropped_img)
        
        # Formulaire pour ajouter le produit au CSV
        st.subheader("2. Informations du produit")
        with st.form(key="add_product_form", clear_on_submit=True):
            p_nom = st.text_input("Nom du produit (ex: Edamame)")
            p_cat = st.text_input("Catégorie (ex: Starters)")
            p_prix = st.text_input("Prix (ex: 35)")
            p_desc = st.text_area("Description")
            
            submit_button = st.form_submit_button(label="Enregistrer & Uploader l'image")
            
            if submit_button:
                if not p_nom:
                    st.warning("Le nom du produit est obligatoire.")
                else:
                    with st.spinner("Upload de l'image sur ImgBB..."):
                        # Convertir l'image découpée en bytes
                        img_byte_arr = io.BytesIO()
                        cropped_img.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        # Envoyer à ImgBB
                        image_url = upload_to_imgbb(img_bytes, IMGBB_API_KEY)
                        
                        if image_url:
                            # Ajouter au DataFrame
                            new_row = {
                                "nom": p_nom,
                                "category": p_cat,
                                "prix": p_prix,
                                "description": p_desc,
                                "image_url": image_url
                            }
                            st.session_state.menu_data = pd.concat([st.session_state.menu_data, pd.DataFrame([new_row])], ignore_index=True)
                            st.success(f"✅ {p_nom} ajouté avec succès !")

# Étape 3 : Affichage et Export du CSV final
st.header("3. Votre Catalogue Final (CSV)")

if not st.session_state.menu_data.empty:
    st.dataframe(st.session_state.menu_data)
    
    # Bouton de téléchargement
    csv_data = st.session_state.menu_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger le catalogue complet (CSV)",
        data=csv_data,
        file_name='catalogue_bamboo_complet.csv',
        mime='text/csv',
    )
else:
    st.info("Aucun produit ajouté pour le moment.")
