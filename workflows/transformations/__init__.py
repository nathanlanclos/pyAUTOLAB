import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as mcolors
import re
import string
import io

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

    # Step 2: Define Transformation Scheme
    st.subheader("Define Transformation Scheme")

    all_to_all = st.checkbox("All plasmids to all hosts?")

    transformation_count = 0

    if not all_to_all:
        st.write("Assign each plasmid to specific hosts using the format below:")
        for plasmid in plasmid_name_list:
            st.text(f"{plasmid} to host(s):")
            host_input = st.text_input(
                f"Hosts for {plasmid} (Row letters, Column numbers, or specific cells/ranges)",
                placeholder="e.g., A, B, C or 1, 2, 3 or A1-B2, C3",
            )
            assigned_cells = parse_host_input(host_input)
            st.write(f"Hosts assigned for {plasmid}: {assigned_cells}")
            transformation_count += len(assigned_cells)
    else:
        transformation_count = num_hosts * num_plasmids

    # Analyze Transformation Scheme
    st.write("Transformation scheme defined. Analyze total transformations below.")
    st.write(f"Total Transformations: {transformation_count}")

    # Step 3: Request Replicates
    replicates = st.number_input("Number of Replicates", min_value=1, step=1, value=1)
    total_transformations = transformation_count * replicates
    st.write(f"Total Wells Needed: {total_transformations}")

    # Step 4: Suggest E-Plate Scheme
    eplate_scheme = generate_eplate_scheme(total_transformations)
    st.write("Suggested E-Plate Scheme:")
    st.dataframe(eplate_scheme)

    # Step 5: Dispense Volumes
    st.subheader("Dispense Volumes")
    plasmid_vol = st.number_input("Plasmid Volume (nl)", min_value=0, value=300, step=10, key="plasmid_vol")
    cells_vol = st.number_input("Cells Volume (nl)", min_value=0, value=3000, step=10, key="cells_vol")

    # Step 6: Define Electroporation Parameters
    st.subheader("Define Electroporation Parameters")
    voltage = st.number_input("Set Voltage (V)", min_value=0, value=180, step=10, key="voltage")
    transfer_time = st.number_input("Set Transfer Time (ms)", min_value=0, value=5, step=1, key="transfer_time")

    # Electroporation Table
    if "electroporation_table" not in st.session_state:
        st.session_state["electroporation_table"] = generate_electroporation_table(eplate_scheme, voltage, transfer_time)

    st.write("Electroporation Conditions Table:")
    electroporation_editor = st.data_editor(
        st.session_state["electroporation_table"],
        use_container_width=True,
        key="electroporation_editor",
    )

    if st.button("Fill Electroporation Table from Inputs"):
        st.session_state["electroporation_table"] = generate_electroporation_table(eplate_scheme, voltage, transfer_time)

    # Machine Selection
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
        csv_data = generate_csv(machine, st.session_state["source_plate"], eplate_scheme, plasmid_vol, cells_vol, replicates, voltage, transfer_time)
        if csv_data:
            st.download_button(
                label=f"Download {machine} CSV",
                data=csv_data.getvalue(),
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

def parse_host_input(input_text):
    """
    Parse the host input for rows, columns, or specific cell ranges.
    """
    cells = []
    input_text = input_text.replace(" ", "")
    for entry in input_text.split(","):
        if "-" in entry:
            start, end = entry.split("-")
            cells.extend(expand_range(start, end))
        else:
            cells.append(entry)
    return cells

def expand_range(start, end):
    """
    Expand a range of cells (e.g., A1-B3).
    """
    start_row, start_col = start[0], int(start[1:])
    end_row, end_col = end[0], int(end[1:])
    expanded = []
    for row in range(ord(start_row), ord(end_row) + 1):
        for col in range(start_col, end_col + 1):
            expanded.append(f"{chr(row)}{col}")
    return expanded

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

def generate_eplate_scheme(total_transformations):
    """
    Generate the eplate scheme based on the total transformations.
    """
    rows = 16
    cols = 24
    plate = pd.DataFrame("", index=list(string.ascii_uppercase[:rows]), columns=[str(i + 1) for i in range(cols)])

    if total_transformations <= 48:
        fill_positions = [(r, c) for r in range(15) for c in range(12) if c % 2 == 0 and r % 2 == 0]
    elif total_transformations <= 96:
        fill_positions = [(r, c) for r in range(16) for c in range(24) if c % 2 == 0 and r % 2 == 0]
    elif total_transformations <= 192:
        fill_positions = [(r, c) for r in range(16) for c in range(24) if (c % 2 == 0 or c % 2 == 1) and r % 2 == 0]
    elif total_transformations <= 288:
        fill_positions = [(r, c) for r in range(16) for c in range(24) if (c % 2 == 0 or c % 2 == 1) and (r % 2 == 0 or r % 2 == 1)]
    else:
        fill_positions = [(r, c) for r in range(16) for c in range(24)]

    for r, c in fill_positions[:total_transformations]:
        plate.iloc[r, c] = "X"

    return plate

import pandas as pd

def generate_electroporation_table(eplate_scheme, voltage=180, transfer_time=5):
    """
    Generate an electroporation conditions table based on the eplate_scheme in the desired format.
    """
    # Define rows and columns for the e-plate
    rows = list("ABCDEFGHIJKLMNOP")
    cols = [f"Column {i + 1}" for i in range(24)]

    # Create an empty DataFrame with MultiIndex for sub-column headers
    col_tuples = []
    for col in cols:
        col_tuples.append((col, "Vₚ (V)"))
        col_tuples.append((col, "τ (ms)"))
    
    # Create a MultiIndex for the columns
    multi_index = pd.MultiIndex.from_tuples(col_tuples, names=["Column", None])

    # Initialize the DataFrame with NaN values
    electroporation_table = pd.DataFrame(index=rows, columns=multi_index)

    # Fill in the table based on the eplate_scheme
    for r in range(eplate_scheme.shape[0]):
        for c in range(eplate_scheme.shape[1]):
            if eplate_scheme.iloc[r, c] == "X":
                row_label = rows[r]
                col_label = cols[c]
                electroporation_table.loc[row_label, (col_label, "Vₚ (V)")] = voltage
                electroporation_table.loc[row_label, (col_label, "τ (ms)")] = transfer_time

    # Add row labels to the first column
    electroporation_table.reset_index(inplace=True)
    electroporation_table.rename(columns={"index": "Row"}, inplace=True)

    return electroporation_table


def generate_csv(machine, source_plate, eplate_scheme, plasmid_vol, cells_vol, replicates, voltage, transfer_time):
    """
    Generate a CSV file based on the source plate layout and eplate scheme.
    """
    if machine != "Echo 550" and machine != "HTP Electroporator (Randy)":
        return None

    source_data = source_plate.stack().reset_index()
    source_data.columns = ["Source Row", "Source Column", "Content"]
    source_data = source_data[source_data["Content"] != ""]

    eplate_data = eplate_scheme.stack().reset_index()
    eplate_data.columns = ["Dest Row", "Dest Column", "Content"]
    eplate_data = eplate_data[eplate_data["Content"] == "X"]

    csv_entries = []

    if machine == "Echo 550":
        for _, source_row in source_data.iterrows():
            source_well = f"{source_row['Source Row']}{source_row['Source Column']}"
            content = source_row['Content']
            if "Plasmid" in content:
                for _, dest_row in eplate_data.iterrows():
                    dest_well = f"{dest_row['Dest Row']}{dest_row['Dest Column']}"
                    csv_entries.append([source_well, "Source Plate", dest_well, "Destination Plate", plasmid_vol])
            elif "Host" in content:
                assigned_dest_wells = eplate_data.iloc[:replicates]
                for _, dest_row in assigned_dest_wells.iterrows():
                    dest_well = f"{dest_row['Dest Row']}{dest_row['Dest Column']}"
                    csv_entries.append([source_well, "Source Plate", dest_well, "Destination Plate", cells_vol])
                eplate_data = eplate_data.iloc[replicates:]

    elif machine == "HTP Electroporator (Randy)":
        csv_buffer = io.StringIO()
        st.session_state["electroporation_table"].to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer

    if not csv_entries:
        return None

    if machine == "Echo 550":
        csv_df = pd.DataFrame(csv_entries, columns=["Source Well", "Source Plate Name", "Destination Well", "Destination Plate Name", "Volume"])

        csv_buffer = io.StringIO()
        csv_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer

# Run the Streamlit app
if __name__ == "__main__":
    render_transformations_workflow()
