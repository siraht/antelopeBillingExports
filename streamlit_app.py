import streamlit as st
import csv
import io
from datetime import datetime, timedelta

# ---------------------------
# Transformation Logic
# ---------------------------

default_columns_to_remove = [
    'Client Email', 'Client Timezone', 'Client State', 'Current Status', 'DOB',
    'Primary Insurance', 'Phone Number', 'Scheduled By', 'Date of Last Status Change',
    'Scheduled Length', 'Actual Duration', 'Contact Type', 'Location', 'Reason', 'Notes',
    "Client's Current Group", 'Scheduled At',
    'Number of Times Rescheduled By Client', 'Tags', 'Charting Note Locked',
    'Referring Physician 1 Name', 'Referring Physician 1 Phone', 'Referring Physician 1 Fax',
    'Referring Physician 2 Name', 'Referring Physician 2 Phone', 'Referring Physician 2 Fax',
    'Referring Physician 3 Name', 'Referring Physician 3 Phone', 'Referring Physician 3 Fax'
]

cpt_code_mapping = {
    'Teen Group Session': '90853',
    'Parent Group': '90853',
    'Individual Therapy Session - 60 minutes': '90837',
    'Mentor Session - 45 minutes': 'H0038 - 3',
    'Individual Therapy Session - 45 minutes': '90834',
    'Case Consultation': '90846, 90832',
    'Parent Coaching Session': '90846',
    'Family Therapy Session': '90847',
    'Evaluation Session': '90791',
    'Psychological Assessment': '90791',
    'Parent Coaching Session - 30 minutes': '90846',
    'Individual Therapy Session 30 minutes': '90832',
    'Individual Therapy Session': '90832',  # For cleaned appointment types
    'Mentor Session - 30 minutes': 'H0038 - 2',
    'Mentor Session - 60 minutes': 'H0038 - 4',
    'Parent Coaching Session - Group Appointment': '90846',
    'Health and Wellness Session': 'H2014',
    'Onboarding Appointment': '90791',
    'In-School Session': '90837',
    'Family Evaluation Session': '90791',
    'Individual Therapy Session  30 minutes': '90832',
    'Teen Evaluation Session': '90791'
}

header_mapping = {
    'Date Fixed': 'Date',
    'Name': 'Client Name',
    'Unique ID': 'Unique ID',
    'Group Attendance': 'Group Attendance',
    'Provider': 'Provider',
    'Status': 'Status',
    'Appointment Type': 'Appointment Type',
    'Chart Note Written': 'Chart Note Written',
    'Missing Info': 'Missing Info',
    'Appointment ID': 'Appointment ID',
    'CPT Code': 'CPT Code'
}

spreadsheet_headers = [
    'Billed', 'CMS1500', 'Family ID', 'Unique ID', 'Appointment ID', 'Date Fixed', 'Week', 'Month',
    'Appointment Type', 'CPT Code', 'Provider', 'Status', 'Billing Status',
    'Name', 'Group Attendance', 'Chart Note Written', 'Missing Info'
]


def process_csv(input_csv, remove_cols=None):
    """
    Processes the uploaded CSV data, transforming it according to the logic
    in your original Python script. Returns the output CSV as a string.
    """

    if remove_cols is None:
        remove_cols = default_columns_to_remove

    # Read CSV from the in-memory file object
    reader = csv.DictReader(io.StringIO(input_csv.decode('utf-8')))
    fieldnames = reader.fieldnames

    # Determine columns to remove
    columns_to_remove = [c for c in remove_cols if c in fieldnames]

    # Prepare an in-memory buffer for writing the transformed CSV
    output_buffer = io.StringIO()
    writer = csv.DictWriter(output_buffer, fieldnames=spreadsheet_headers)
    writer.writeheader()

    for row in reader:
        # If a column is in columns_to_remove, we can ignore it, but the main logic doesn't need them anyway.

        # Split group appointments
        client_names = [name.strip() for name in row['Client Name'].split(',')]
        num_clients = len(client_names)

        def get_field_values(field_name):
            field_value = row.get(field_name, '')
            if field_value.strip():
                values = [item.strip() for item in field_value.split(',')]
            else:
                values = []
            if len(values) < num_clients:
                values.extend([''] * (num_clients - len(values)))
            elif len(values) > num_clients:
                values = values[:num_clients]
            return values

        unique_ids = get_field_values('Unique ID')
        group_attendance = get_field_values('Group Attendance')
        diagnosis_codes = get_field_values("Client's Diagnosis Codes")

        # Original Appointment Type
        original_appointment_type = row.get('Appointment Type', '')
        normalized_original_appointment_type = ' '.join(original_appointment_type.strip().split())

        # Clean up Appointment Type
        appointment_type = normalized_original_appointment_type
        if ' - ' in appointment_type:
            appointment_type = appointment_type.split(' - ')[0]
        elif '  ' in appointment_type:
            appointment_type = appointment_type.split('  ')[0]
        elif ' ' in appointment_type and appointment_type.split(' ')[-1].endswith('minutes'):
            appointment_type = ' '.join(appointment_type.split(' ')[:-2])

        # Extract date and time
        original_date_time = row.get('Date', '')
        date_only, time_only, date_for_id, time_for_id = '', '', '', ''

        if original_date_time:
            try:
                # e.g. "YYYY-MM-DD HH:MM:SS ZZZ"
                date_time_obj = datetime.strptime(original_date_time, '%Y-%m-%d %H:%M:%S %Z')
                date_only = date_time_obj.strftime('%Y-%m-%d')
                time_only = date_time_obj.strftime('%H%M')
                date_for_id = date_time_obj.strftime('%m%d%y')
                time_for_id = date_time_obj.strftime('%H%M')
            except ValueError:
                # Try removing last 4 characters for timezone
                try:
                    date_time_obj = datetime.strptime(original_date_time[:-4], '%Y-%m-%d %H:%M:%S')
                    date_only = date_time_obj.strftime('%Y-%m-%d')
                    time_only = date_time_obj.strftime('%H%M')
                    date_for_id = date_time_obj.strftime('%m%d%y')
                    time_for_id = date_time_obj.strftime('%H%M')
                except ValueError:
                    pass

        # Compute Week and Month
        week_str, month_str = '', ''
        if date_only:
            try:
                date_obj = datetime.strptime(date_only, '%Y-%m-%d')
                week_start = date_obj - timedelta(days=date_obj.weekday())
                week_str = week_start.strftime('%-m/%-d/%Y')
                month_str = date_obj.strftime('%B %y')
            except ValueError:
                pass

        # Abbreviations
        def abbreviate(text):
            if not text:
                return ''
            words = text.strip().split()
            abbreviation = ''.join(word[0].upper() for word in words)
            return abbreviation

        appointment_type_abbr = abbreviate(appointment_type)
        provider_abbr = abbreviate(row.get('Provider', ''))

        # Process each client
        for i in range(num_clients):
            new_row = {}
            for sh in spreadsheet_headers:
                if sh in ['Billed', 'Family ID', 'Billing Status']:
                    new_row[sh] = ''
                elif sh == 'Date Fixed':
                    new_row[sh] = date_only
                elif sh == 'Week':
                    new_row[sh] = week_str
                elif sh == 'Month':
                    new_row[sh] = month_str
                elif sh == 'Appointment ID':
                    unique_id = unique_ids[i] if i < len(unique_ids) else ''
                    appointment_id = f"{date_for_id}-{time_for_id}-{unique_id}-{appointment_type_abbr}-{provider_abbr}"
                    new_row[sh] = appointment_id
                elif sh == 'CMS1500':
                    unique_id = unique_ids[i] if i < len(unique_ids) else ''
                    cms1500_url = f"https://secure.gethealthie.com/cms1500s/new/?patient_id={unique_id}" if unique_id else ''
                    new_row[sh] = cms1500_url
                elif sh == 'CPT Code':
                    cpt_code = cpt_code_mapping.get(normalized_original_appointment_type, '')
                    new_row[sh] = cpt_code
                else:
                    csv_header = header_mapping.get(sh)
                    if csv_header:
                        if csv_header == 'Client Name':
                            value = client_names[i]
                        elif csv_header == 'Unique ID':
                            value = unique_ids[i] if i < len(unique_ids) else ''
                        elif csv_header == 'Group Attendance':
                            value = group_attendance[i] if i < len(group_attendance) else ''
                        else:
                            value = row.get(csv_header, '')
                        new_row[sh] = value
                    else:
                        new_row[sh] = ''

            # Update Status for group appointments
            if num_clients > 1:
                ga = new_row.get('Group Attendance', '').strip().lower()
                if ga == 'yes':
                    new_row['Status'] = 'Occurred'
                elif ga == 'no':
                    new_row['Status'] = 'Did not attend'

            # Missing Info
            missing_info = []

            # Attendance check (only for group appointments)
            if num_clients > 1:
                if not new_row.get('Group Attendance', '').strip():
                    missing_info.append('Attendance')

            # Status check
            status_value = new_row.get('Status', '').strip()
            if not status_value:
                missing_info.append('Status')

            # Chart Note Written check
            chart_note_written = new_row.get('Chart Note Written', '').strip().lower()
            if chart_note_written == 'no' or not chart_note_written:
                missing_info.append('Note')

            # Check for missing Diagnosis Codes for CPT 90791 and Status 'Occurred'
            cpt_code = new_row.get('CPT Code', '')
            status = new_row.get('Status', '').strip()
            if cpt_code == '90791' and status == 'Occurred':
                diagnosis_code = diagnosis_codes[i] if i < len(diagnosis_codes) else ''
                if not diagnosis_code.strip():
                    missing_info.append('Diagnosis')

            new_row['Missing Info'] = ', '.join(missing_info) if missing_info else ''

            writer.writerow(new_row)

    return output_buffer.getvalue()

# ---------------------------
# Streamlit App
# ---------------------------

def main_app():
    st.title("Antelope Appointment Data Transformer 🫡")

    st.markdown(
        """
        **Instructions**:
        1. Download an Appointment export from Healthie from the previous Friday through current Thursday.
        2. Upload that CSV here.
        3. Download the outputted CSV from here.
        4. Open the CSV on your local machine and copy and paste the content of the outputted CSV into the Data sheet of the Billing+Client List spreadsheet.
        """
    )

    # File uploader
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    
    # Optional: Let user specify columns to remove, or just use defaults
    # For simplicity, we'll skip adding a custom remove list UI. If you want to add it:
    # remove_cols_input = st.text_input("Enter columns to remove (comma-separated)", "")

    if uploaded_file is not None:
        # Process the CSV
        # remove_cols = [col.strip() for col in remove_cols_input.split(',')] if remove_cols_input else None
        output_csv_str = process_csv(uploaded_file.read())  # Pass the file content to the process function

        st.success("Transformation complete! You can now download the transformed CSV below.")

        # Download button
        st.download_button(
            label="Download Transformed CSV",
            data=output_csv_str,
            file_name="transformed_output.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main_app()
