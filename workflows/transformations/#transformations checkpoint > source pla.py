#transformations checkpoint > source plate logic working
import re
import streamlit as st
import pandas as pd
import string

def render_transformations_workflow():
    st.header("Transformations Workflow")

    # Step 1: Input Parameters
    st.subheader("Experiment Parameters")
    num_hosts = st.number_input("Number of Hosts", min_value=1, step=1, value=1, key="num_hosts")
    host_names = st.text_area(
        "Optional: Enter Host Names (separated by spaces, commas, or new lines)",
        placeholder="e.g., Host A, Host B, Host C",
        key="host_names",
    )
    num_plasmids = st.number_input("Number of Plasmids", min_value=1, step=1, value=1, key="num_plasmids")
    plasmid_names = st.text_area(
        "Optional: Enter Plasmid Names (separated by spaces, commas, or new lines)",
        placeholder="e.g., Plasmid 1, Plasmid 2, Plasmid 3",
        key="plasmid_names",
    )
    plate_size = st.selectbox("Plate Size", [96, 384], key="plate_size")

    # Process user-provided names
    host_name_list = parse_names(host_names)
    plasmid_name_list = parse_names(plasmid_names)

    # Check for name mismatches
    warnings = []
    if len(host_name_list) < num_hosts:
        missing_hosts = [f"Host {i + 1}" for i in range(len(host_name_list), num_hosts)]
        warnings.append(f"Warning: Not enough host names provided, auto-labeling: {', '.join(missing_hosts)}")
    elif len(host_name_list) > num_hosts:
        extra_hosts = host_name_list[num_hosts:]
        warnings.append(
            f"Warning: Too many host names provided, did you specify the correct number? Unused names: {', '.join(extra_hosts)}"
        )

    if len(plasmid_name_list) < num_plasmids:
        missing_plasmids = [f"Plasmid {i + 1}" for i in range(len(plasmid_name_list), num_plasmids)]
        warnings.append(f"Warning: Not enough plasmid names provided, auto-labeling: {', '.join(missing_plasmids)}")
    elif len(plasmid_name_list) > num_plasmids:
        extra_plasmids = plasmid_name_list[num_plasmids:]
        warnings.append(
            f"Warning: Too many plasmid names provided, did you specify the correct number? Unused names: {', '.join(extra_plasmids)}"
        )

    # Initialize session state for source plate
    if "source_plate" not in st.session_state or st.session_state.get("last_plate_size") != plate_size:
        st.session_state["source_plate"] = generate_source_plate(
            num_hosts, num_plasmids, plate_size, host_name_list, plasmid_name_list
        )
        st.session_state["last_plate_size"] = plate_size

    # Display the source plate
    st.subheader("Source Plate Organization")
    plate_editor = st.data_editor(
        st.session_state["source_plate"],
        use_container_width=True,
        key="source_plate_editor",
    )

    # Display warnings if any
    if warnings:
        for warning in warnings:
            st.warning(warning)

    st.write("You can modify the layout directly above or use the buttons to clear or auto-assign.")

    # Buttons for Clear and Auto Assign
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear"):
            clear_source_plate()
    with col2:
        if st.button("Auto Assign"):
            st.session_state["source_plate"] = generate_source_plate(
                num_hosts, num_plasmids, plate_size, host_name_list, plasmid_name_list
            )

    # Step 2: Machine Selection
    st.subheader("Machine Selection")
    machines = {
        "Dispense to Eplate": "Echo 550",
        "Run Electroporator": "HTP Electroporator (Randy)",
        "Rescue Cells": "Hamilton Vantage",
        "Plate Cells": "Biomek NXP",
        "Pick Cells": "Qpix",
    }

    selected_machines = {}
    for step, default_machine in machines.items():
        selected_machines[step] = st.selectbox(step, [default_machine])

    # Protocol and CSV Output
    st.subheader("Protocol and CSV Outputs")
    for step, machine in selected_machines.items():
        st.write(f"Step: {step} | Machine: {machine}")
        st.download_button(
            label=f"Download {machine} CSV",
            data=generate_csv(machine, st.session_state["source_plate"]),
            file_name=f"{machine.replace(' ', '_')}_protocol.csv",
            mime="text/csv",
        )

    # Link to protocol PDF
    st.markdown(f"[Download Full Protocol (PDF)](protocols/transformations_protocol.pdf)")


def parse_names(input_text):
    """
    Parse names from a text input, allowing separation by spaces, commas, or new lines.
    """
    return [name.strip() for name in re.split(r"[,\s\n]+", input_text) if name.strip()]


def generate_source_plate(num_hosts, num_plasmids, plate_size, host_names, plasmid_names):
    # Determine plate dimensions
    rows = 8 if plate_size == 96 else 16
    cols = 12 if plate_size == 96 else 24
    row_labels = list(string.ascii_uppercase[:rows])
    col_labels = [str(i + 1) for i in range(cols)]

    # Create a blank plate layout
    plate = pd.DataFrame("", index=row_labels, columns=col_labels)

    # Add plasmids to the plate
    current_row = 0
    current_col = 0
    for plasmid in range(num_plasmids):
        plasmid_name = plasmid_names[plasmid] if plasmid < len(plasmid_names) else f"Plasmid {plasmid + 1}"
        plate.iloc[current_row, current_col] = plasmid_name
        current_col += 1
        if current_col >= cols:
            current_row += 1
            current_col = 0

    # Determine starting row for hosts
    host_start_row = current_row + 2 if current_row + 2 < rows else current_row + 1

    # Add hosts to the plate
    current_row = host_start_row
    current_col = 0
    for host in range(num_hosts):
        host_name = host_names[host] if host < len(host_names) else f"Host {host + 1}"
        plate.iloc[current_row, current_col] = host_name
        current_col += 1
        if current_col >= cols:
            current_row += 1
            current_col = 0

    return plate


def clear_source_plate():
    # Clear the source plate (set all cells to blank, preserving layout)
    plate = st.session_state["source_plate"]
    st.session_state["source_plate"] = plate.applymap(lambda x: "")


def generate_csv(machine, plate_layout):
    # Example CSV generation using plate layout
    csv_data = plate_layout.stack().reset_index()
    csv_data.columns = ["Row", "Column", "Content"]
    csv_data = csv_data[csv_data["Content"] != ""]
    return csv_data.to_csv(index=False)
