import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime

# Add the root directory of the project to the Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# Define paths for the protocols folder and metadata file
protocols_dir = os.path.join(root_dir, "protocols")
metadata_file_path = os.path.join(protocols_dir, "protocol_metadata.csv")

if not os.path.exists(protocols_dir):
    os.makedirs(protocols_dir)  # Create protocols directory if it doesn't exist

# Ensure metadata file exists
if not os.path.exists(metadata_file_path):
    pd.DataFrame(columns=["file_name", "uploader", "description", "date"]).to_csv(metadata_file_path, index=False)

def render_landing_page():
    """Render a simple landing page."""
    st.title("Welcome to pyAUTOlab")
    st.write("""
    This is the landing page for pyAUTOlab, a streamlined automation platform for laboratory workflows.
    Please use the navigation panel on the left to explore different workflows.
    """)

def render_protocols_page():
    st.title("Protocols Repository")

    # Upload Section
    st.subheader("Upload a Protocol")

    uploader_name = st.text_input("Your Name")
    protocol_description = st.text_area("Protocol Description", placeholder="Briefly describe the protocol...")
    uploaded_file = st.file_uploader("Choose a protocol file to upload", type=["pdf", "docx", "txt"])

    if uploaded_file and uploader_name and protocol_description:
        if st.button("Upload Protocol"):
            # Save the file
            file_path = os.path.join(protocols_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Record metadata
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metadata = pd.read_csv(metadata_file_path)
            new_entry = {
                "file_name": uploaded_file.name,
                "uploader": uploader_name,
                "description": protocol_description,
                "date": upload_date
            }
            metadata = metadata.append(new_entry, ignore_index=True)
            metadata.to_csv(metadata_file_path, index=False)

            st.success(f"File '{uploaded_file.name}' uploaded successfully.")

    elif uploaded_file:
        st.warning("Please fill in your name and a description before uploading.")

    # Display Available Protocols
    st.subheader("Available Protocols")

    if os.path.exists(metadata_file_path):
        metadata = pd.read_csv(metadata_file_path)

        if not metadata.empty:
            for index, row in metadata.iterrows():
                with st.container():
                    st.write(f"**Protocol Name**: {row['file_name']}")
                    st.write(f"**Uploader**: {row['uploader']}")
                    st.write(f"**Description**: {row['description']}")
                    st.write(f"**Date Uploaded**: {row['date']}")
                    file_path = os.path.join(protocols_dir, row['file_name'])
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    st.download_button(
                        label=f"Download {row['file_name']}",
                        data=file_bytes,
                        file_name=row['file_name'],
                        mime="application/octet-stream"
                    )
                    st.markdown("---")
        else:
            st.info("No protocols have been uploaded yet.")
    else:
        st.info("No protocols have been uploaded yet.")

def main():
    st.set_page_config(page_title="pyAUTOlab", layout="wide")

    # Sidebar for workflow selection
    st.sidebar.title("Navigation")
    workflow = st.sidebar.selectbox("Choose a Workflow", ["Landing Page", "Transformations", "Live Visualization", "Protocols"])

    if workflow == "Landing Page":
        render_landing_page()
    elif workflow == "Transformations":
        # Assuming `render_transformations_workflow` function exists
        st.title("Transformations Workflow")
        from workflows.transformations import render_transformations_workflow
        render_transformations_workflow()
    elif workflow == "Live Visualization":
        if "transformation_assignments" in st.session_state:
            render_live_visualization(st.session_state["transformation_assignments"])
        else:
            st.warning("Please complete the transformations workflow before viewing the visualization.")
    elif workflow == "Protocols":
        render_protocols_page()

if __name__ == "__main__":
    main()
