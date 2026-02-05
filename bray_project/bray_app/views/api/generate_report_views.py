# Imports for report generation
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from django.db import connection
from openpyxl import Workbook
from io import BytesIO
from datetime import datetime
from bray_app.src import HmiAddress 
from bray_app.views.api.configuration_api_views import TestleadSmartsyncx



def getstatus(num):
    if TestleadSmartsyncx is None:
        print("[Error] HMI connection not established.")
        return None 
    try:
        return TestleadSmartsyncx.read_holding_registers(num, 1).registers[0]
    except Exception as e:
        print(f"[Error] Failed to read from register {num}: {e}")
        return None
 


def export_station_data(valve_serial_no, station_num):
    """
    Export current_status_station1 or current_status_station2 table data to E drive as Excel file
    """
    try:
        print(f"[EXPORT_EXCEL] Starting Excel export for valve {valve_serial_no}, station {station_num}")
        
        # Get count id from temp_pressure_analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT_ID
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
            """, [valve_serial_no])
            
            count_row = cursor.fetchone()
            count_id = count_row[0] if count_row else "0"
            print(f"[EXPORT_EXCEL] Count ID: {count_id}")
        
        # Create E drive directory if it doesn't exist
        e_drive_path = "D:/Bray_0.5_DB_export"
        os.makedirs(e_drive_path, exist_ok=True)
        print(f"[EXPORT_EXCEL] Export directory: {e_drive_path}")
        
        # Generate filename with serial number and count id
        filename = f"{valve_serial_no}_{count_id}_0.5MT.xlsx"
        filepath = os.path.join(e_drive_path, filename)
        print(f"[EXPORT_EXCEL] Excel file path: {filepath}")
        
        # Determine which table to query based on station number
        station_table = 'current_status_station1' if station_num == 1 else 'current_status_station2'
        print(f"[EXPORT_EXCEL] Querying table: {station_table}")
        
        # Fetch data from database
        with connection.cursor() as cursor:
            query = f"""
                SELECT id, VALVE_SERIAL_NO, PRESSURE, TEST_ID, TEST_NAME,  
                        DATE_TIME, TIMER_STATUS, RESULT
                FROM {station_table}
                WHERE VALVE_SERIAL_NO = %s
                ORDER BY id 
            """
            cursor.execute(query, [valve_serial_no])
            
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            print(f"[EXPORT_EXCEL] Found {len(rows)} data rows")
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"Station {station_num} Data"
        
        # Write headers
        ws.append(columns)
        
        # Write data rows
        for row in rows:
            ws.append(row)
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to E drive
        wb.save(filepath)
        print(f"[EXPORT_EXCEL] Excel file successfully saved: {filepath}")
        
        return True
        
    except Exception as e:
        print(f"[EXPORT_EXCEL] Error exporting Excel file: {e}")
        import traceback
        traceback.print_exc()
        return False
        
        return True
        
    except Exception as e:
        print(f"[EXPORT] Failed to export data: {e}")
        import traceback
        traceback.print_exc()
        return False
    



def graph_generation_from_excel(excel_filepath, test_id, test_name):
    """
    Generate modern, professional pressure vs time graph for a single test from Excel file
    Returns None if test has no timer on/off events (should be omitted from report)
    """
    try:
        from openpyxl import load_workbook
        from datetime import datetime
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from io import BytesIO
        import base64

        # ---------------- LOAD EXCEL ----------------
        wb = load_workbook(excel_filepath)
        ws = wb.active

        date_times = []
        pressures = []
        timer_status = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[3] == test_id:
                date_time = row[5]
                pressure = row[2]
                timer_stat = row[6]

                if date_time and pressure is not None:
                    if isinstance(date_time, str):
                        try:
                            date_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                        except:
                            continue

                    date_times.append(date_time)
                    pressures.append(float(pressure))
                    timer_status.append(int(timer_stat) if timer_stat is not None else 0)

        if not date_times:
            wb.close()
            return "NO_GRAPH"

        # ---------------- TIMER CHECK ----------------
        has_timer_on = any(s == 1 for s in timer_status)
        has_timer_off_after_on = False

        timer_was_on = False
        for s in timer_status:
            if s == 1:
                timer_was_on = True
            elif s == 0 and timer_was_on:
                has_timer_off_after_on = True
                break

        if not has_timer_on or not has_timer_off_after_on:
            wb.close()
            return "NO_GRAPH"

        # ---------------- FIND TIMER WINDOW ----------------
        timer_start_time = None
        timer_stop_time = None

        for i in range(len(timer_status)):
            if timer_status[i] == 1 and timer_start_time is None:
                timer_start_time = date_times[i]

            if timer_start_time and timer_status[i] == 0:
                timer_stop_time = date_times[i]
                break

        # ---------------- MODERN FIGURE ----------------
        fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
        
        # Modern Color Palette
        COLOR_BG = '#FFFFFF'
        COLOR_PLOT_BG = '#FFFFFF'
        COLOR_PRIMARY = '#2563EB'  # Vibrant Blue (Royal Blue)
        COLOR_GRID = '#E2E8F0'     # Light Slate
        COLOR_TEXT = '#475569'     # Slate 600
        COLOR_TITLE = '#1E293B'    # Slate 800
        COLOR_START = '#10B981'    # Emerald 500
        COLOR_STOP = '#EF4444'     # Red 500

        # Background Configuration
        fig.patch.set_facecolor(COLOR_BG)
        ax.set_facecolor(COLOR_PLOT_BG)

        # ---------------- PRESSURE LINE ----------------
        ax.plot(date_times, pressures, color=COLOR_PRIMARY, linewidth=2.5, solid_capstyle='round', zorder=3)

        # Soft Gradient Fill
        ax.fill_between(date_times, pressures, 0, color=COLOR_PRIMARY, alpha=0.10, zorder=2)

        # ---------------- TIMER MARKERS ----------------
        # Get Y-axis limits for label positioning
        # We plot first so limits are set
        y_min, y_max = ax.get_ylim()
        
        # Start Line
        ax.axvline(x=timer_start_time, color=COLOR_START, linestyle='--', linewidth=1.5, zorder=4)

        # Stop Line
        ax.axvline(x=timer_stop_time, color=COLOR_STOP, linestyle='--', linewidth=1.5, zorder=4)

        # Text Annotations for Start/Stop
        # Using y_max for positioning
        ax.text(timer_start_time, y_max, ' START', color=COLOR_START, fontsize=10, fontweight='bold', va='bottom', ha='left', rotation=90)
        ax.text(timer_stop_time, y_max, ' STOP', color=COLOR_STOP, fontsize=10, fontweight='bold', va='bottom', ha='right', rotation=90)

        # Range Highlight
        ax.axvspan(timer_start_time, timer_stop_time, color=COLOR_START, alpha=0.05, zorder=1)

        # ---------------- AXIS STYLING ----------------
        ax.set_title(test_name, fontsize=16, fontweight='bold', color=COLOR_TITLE, pad=20)
        ax.set_xlabel('Time', fontsize=11, fontweight='500', color=COLOR_TEXT, labelpad=10)
        ax.set_ylabel('Pressure', fontsize=11, fontweight='500', color=COLOR_TEXT, labelpad=10)

        # Date/Time Formatting
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=6, maxticks=10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Grid Styling (Clean Horizontal Lines)
        ax.grid(True, axis='y', color=COLOR_GRID, linestyle='-', linewidth=0.5, alpha=0.8)
        ax.grid(False, axis='x')
        ax.set_axisbelow(True)

        # Spines (Borders) - Minimalist
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color(COLOR_GRID)
        ax.spines['bottom'].set_linewidth(1.5)

        # Ticks
        ax.minorticks_on()
        ax.tick_params(axis='both', colors=COLOR_TEXT, labelsize=10)
        ax.tick_params(axis='y', length=0) # Hide Y ticks
        ax.tick_params(axis='x', length=5, color=COLOR_GRID)
        
        # Date rotation
        fig.autofmt_xdate(rotation=0, ha='center')

        # Margins
        ax.margins(x=0.02, y=0.1)

        plt.tight_layout()

        # ---------------- SAVE IMAGE ----------------
        buffer = BytesIO()
        plt.savefig(
            buffer,
            format='png',
            dpi=200,
            bbox_inches='tight',
            facecolor='white'
        )
        buffer.seek(0)

        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        plt.close(fig)
        buffer.close()
        wb.close()

        return f"data:image/png;base64,{image_base64}"

    except Exception as e:
        print(f"[GRAPH] Error generating graph for test {test_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
    

def get_logo_base64():
    """
    Convert the Bray logo to base64 for embedding in PDF
    """
    try:
        from django.conf import settings
        logo_path = os.path.join(settings.BASE_DIR, 'bray_app', 'static', 'images', 'braylogo.webp')
        
        with open(logo_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/webp;base64,{encoded_string}"
    except Exception as e:
        print(f"[LOGO] Error encoding logo: {e}")
        return ""

    
def merged_report(valve_serial_no, station_num):
    """
    Export merged_report.html with test data to E drive as PDF - one page per test
    """
    try:        
        print(f"[EXPORT_PDF] Starting PDF export for valve {valve_serial_no}, station {station_num}")
        
        # Get count id from temp_pressure_analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT_ID
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
                ORDER BY COUNT_ID DESC
                LIMIT 1
            """, [valve_serial_no])
            
            count_row = cursor.fetchone()
            count_id = count_row[0] if count_row else "0"
            print(f"[EXPORT_PDF] Count ID: {count_id}")
            
            # Fetch master data for the valve (common for all tests)
            cursor.execute("""
                SELECT VALVE_SER_NO, VALVESIZE_NAME, COL4_VALUE,
                       COL7_VALUE, COL8_VALUE
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s
            """, [valve_serial_no])
            
            master_row = cursor.fetchone()
            if not master_row:
                print(f"[EXPORT_PDF] No master data found for valve {valve_serial_no}")
                return False
            
            
            serial_no = master_row[0] or ""
            valve_size = master_row[1] or ""
            part_no = master_row[2] or ""
            assembled_by = master_row[3] or ""
            tested_by = master_row[4] or ""
            
            # Fetch ALL test data from pressure_analysis (not just one)
            cursor.execute("""
                SELECT TEST_ID, TEST_NAME, SET_TIME, SET_PRESSURE, 
                       PRESSURE_UNIT, START, END, VALVE_STATUS
                FROM pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
                ORDER BY TEST_ID ASC
            """, [valve_serial_no])
            
            test_rows = cursor.fetchall()
            print(f"[EXPORT_PDF] Found {len(test_rows)} test records")
            
            if not test_rows:
                print(f"[EXPORT_PDF] No test data found for valve {valve_serial_no}")
                return False
        
        # Get report path from configuration_table or use default
        default_path = "D:/Bray_0.5_Reports"
        base_report_path = default_path
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT REPORT_PATH FROM configuration_table")
            path_row = cursor.fetchone()
            
            # Check if database path exists and is valid
            if path_row and path_row[0] and path_row[0].strip():
                configured_path = path_row[0].strip()
                print(f"[EXPORT_PDF] Configured report path: {configured_path}")
                
                # Check if the drive/path is accessible
                try:
                    # Extract drive letter from the configured path
                    drive = os.path.splitdrive(configured_path)[0]
                    
                    # Check if drive exists (for Windows)
                    if drive and not os.path.exists(drive + "/"):
                        print(f"[EXPORT_PDF] Configured drive {drive} not accessible, using default")
                        base_report_path = default_path
                    else:
                        base_report_path = configured_path
                except Exception as e:
                    print(f"[EXPORT_PDF] Error checking configured path: {e}")
                    base_report_path = default_path
            else:
                print(f"[EXPORT_PDF] No path configured, using default: {default_path}")
        
        print(f"[EXPORT_PDF] Using report path: {base_report_path}")
        
        # Create pdf subfolder inside the report path
        pdf_folder_path = os.path.join(base_report_path, "pdf")
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(pdf_folder_path, exist_ok=True)
            print(f"[EXPORT_PDF] PDF folder created/verified: {pdf_folder_path}")
        except Exception as e:
            # Fallback to default path with pdf subfolder
            print(f"[EXPORT_PDF] Error creating PDF folder, using fallback: {e}")
            base_report_path = default_path
            pdf_folder_path = os.path.join(base_report_path, "pdf")
            os.makedirs(pdf_folder_path, exist_ok=True)
            print(f"[EXPORT_PDF] Fallback PDF folder: {pdf_folder_path}")

        # Get current date
        from datetime import datetime
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Get the Excel file path (should be in D:/Bray_DB_export)
        excel_filename = f"{valve_serial_no}_{count_id}_0.5MT.xlsx"
        excel_filepath = os.path.join("D:/Bray_0.5_DB_export", excel_filename)
        print(f"[EXPORT_PDF] Looking for Excel file: {excel_filepath}")
        
        # Check if Excel file exists
        if not os.path.exists(excel_filepath):
            print(f"[EXPORT_PDF] Excel file not found: {excel_filepath}")
            return False
        
        print(f"[EXPORT_PDF] Excel file found, proceeding with graph generation")
        
        # Build HTML content with all test pages
        all_pages_html = ""
        valid_tests = []
        
        # First pass: identify valid tests (those with timer events)
        for test_row in test_rows:
            test_id = test_row[0]
            test_type = test_row[1] or ""
            print(f"[EXPORT_PDF] Processing test {test_id} ({test_type})")

            
            # Generate graph from Excel file to check if test is valid
            print("call the graph function")
            graph_image_base64 = graph_generation_from_excel(excel_filepath, test_id, test_type)
            
            # Only include tests that have timer on/off events
            if graph_image_base64 is not None:
                valid_tests.append((test_row, graph_image_base64))
                print(f"[EXPORT_PDF] Test {test_id} ({test_type}) - valid, graph generated")
            else:
                print(f"[EXPORT_PDF] Skipping test {test_id} ({test_type}) - no timer events")
        
        # Check if we have any valid tests to include in the report
        if len(valid_tests) == 0:
            print(f"[EXPORT_PDF] No valid tests found for valve {valve_serial_no} - no PDF report generated")
            return False
        
        print(f"[EXPORT_PDF] Found {len(valid_tests)} valid tests for PDF generation")
        
        # Second pass: generate HTML for valid tests
        for idx, (test_row, graph_image_base64) in enumerate(valid_tests):
            test_id = test_row[0]
            test_type = test_row[1] or ""
            set_time = test_row[2] if test_row[2] else "0"
            set_pressure = test_row[3] if test_row[3] else "0"
            pressure_unit = test_row[4] if test_row[4] else "bar"
            start_time_raw = test_row[5]
            end_time_raw = test_row[6]
            valve_status = test_row[7] if test_row[7] else "UNKNOWN"
            
            # Format start and end times - extract only time portion
            start_time = ""
            end_time = ""
            
            if start_time_raw:
                if isinstance(start_time_raw, str):
                    # If it's already a string, extract only time portion
                    start_time = start_time_raw
                else:
                    # If it's a datetime object, format to HH:MM:SS
                    start_time = start_time_raw.strftime("%H:%M:%S")
            
            if end_time_raw:
                if isinstance(end_time_raw, str):
                    end_time = end_time_raw
                else:
                    end_time = end_time_raw.strftime("%H:%M:%S")
            
            # Calculate time difference
            time_diff = ""
            if start_time and end_time:
                try:
                    from datetime import datetime
                    start_dt = datetime.strptime(start_time, "%H:%M:%S")
                    end_dt = datetime.strptime(end_time, "%H:%M:%S")
                    diff = end_dt - start_dt
                    time_diff = str(diff)
                except Exception as e:
                    time_diff = "N/A"
            
            # Prepare context data for this test
            context = {
                'serial_no': serial_no,
                'valve_size': valve_size,
                'part_no': part_no,
                'tested_by': tested_by,
                'test_date': current_date,
                'test_type': test_type,
                'set_time': set_time,
                'set_pressure': set_pressure,
                'pressure_unit': pressure_unit,
                'start_time': start_time,
                'end_time': end_time,
                'time_diff': time_diff,
                'valve_status': valve_status,
                'current_date': current_date,
                'graph_image_base64': graph_image_base64,
                'logo_base64': get_logo_base64()  
            }
            
            # Render the template for this test
            page_html = render_to_string('merged_report.html', context)
            
            # Add page break after each page except the last one
            if idx < len(valid_tests) - 1:
                # Add page break style to the body tag
                page_html = page_html.replace('</body>', '<div style="page-break-after: always;"></div></body>')
            
            all_pages_html += page_html
        
        # Generate filename with serial number and count id
        filename = f"{valve_serial_no}_{count_id}_report.pdf"
        filepath = os.path.join(pdf_folder_path, filename)
        print(f"[EXPORT_PDF] Generating PDF: {filepath}")
        
        # Convert combined HTML to PDF using weasyprint
        HTML(string=all_pages_html).write_pdf(filepath)
        print(f"[EXPORT_PDF] PDF successfully generated: {filepath}")
        
        return True
        
    except Exception as e:
        print(f"[EXPORT_PDF] Error generating PDF report: {e}")
        import traceback
        traceback.print_exc()
        return False
    

    
def excel_report(valve_serial_no, station_num):
    """
    Copy Excel template from bray_app/excel to the excel subfolder in report path
    """
    try:
        print(f"[EXCEL_COPY] Starting Excel template copy for valve {valve_serial_no}, station {station_num}")
        import shutil
        today_date = datetime.now().strftime("%d-%m-%Y")
        
        # Get count id from temp_pressure_analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT_ID
                FROM temp_pressure_analysis
                WHERE VALVE_SER_NO = %s
                AND CYCLE_COMPLETE = 'No'
                ORDER BY COUNT_ID DESC
                LIMIT 1
            """, [valve_serial_no])
            
            count_row = cursor.fetchone()
            count_id = count_row[0] if count_row else "0"
            print(f"[EXCEL_COPY] Count ID: {count_id}")
        
        # Get report path from configuration_table or use default
        default_path = "D:/Bray_0.5_Reports"
        base_report_path = default_path
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT REPORT_PATH FROM configuration_table")
            path_row = cursor.fetchone()
            
            # Check if database path exists and is valid
            if path_row and path_row[0] and path_row[0].strip():
                configured_path = path_row[0].strip()
                
                # Check if the drive/path is accessible
                try:
                    # Extract drive letter from the configured path
                    drive = os.path.splitdrive(configured_path)[0]
                    
                    # Check if drive exists (for Windows)
                    if drive and not os.path.exists(drive + "/"):
                        base_report_path = default_path
                    else:
                        base_report_path = configured_path
                except Exception as e:
                    base_report_path = default_path
            else:
                print(f"[EXCEL_COPY] No path configured, using default: {default_path}")
        
        # Create excel subfolder inside the report path
        excel_folder_path = os.path.join(base_report_path, "excel")
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(excel_folder_path, exist_ok=True)
        except Exception as e:
            # Fallback to default path with excel subfolder
            base_report_path = default_path
            excel_folder_path = os.path.join(base_report_path, "excel")
            os.makedirs(excel_folder_path, exist_ok=True)
        
        # Source Excel template path (inside bray_app)
        source_excel_path = os.path.join("bray_app", "excel", "Bray_Excel_Report_20122024_20_12_2024_11_36.xlsx")
        print(f"[EXCEL_COPY] Source template path: {source_excel_path}")
        
        # Check if source file exists
        if not os.path.exists(source_excel_path):
            print(f"[EXCEL_COPY] Source template file not found: {source_excel_path}")
            return False
        
        # Destination filename with valve serial and count id
        destination_filename = f"{valve_serial_no}_{count_id}_template.xlsx"
        destination_filepath = os.path.join(excel_folder_path, destination_filename)
        print(f"[EXCEL_COPY] Destination path: {destination_filepath}")
        
        # Copy the Excel template
        shutil.copy2(source_excel_path, destination_filepath)
        print(f"[EXCEL_COPY] Template file copied successfully")
        
        # Fetch component data from master_temp_data using the current valve serial number
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT VALVE_SER_NO,COL5_VALUE,COL9_VALUE,COL10_VALUE,COL11_VALUE,
                COL12_VALUE,COL13_VALUE,COL14_VALUE,
                COL15_VALUE,COL16_VALUE,COL17_VALUE, 
                COL18_VALUE,COL19_VALUE,COL20_VALUE,
                COL21_VALUE,COL22_VALUE,COL23_VALUE,COL7_VALUE,COL8_VALUE,COL4_VALUE
                FROM master_temp_data
                WHERE VALVE_SER_NO = %s
            """, [valve_serial_no])
            
            serial_data = cursor.fetchone()
            
            if not serial_data:
                # Fallback to using the parameter valve serial number
                valve_serial_from_db = valve_serial_no
                Bray_Order = ""
                Body_Part_No = ""
                Body_Heat_No = ""
                Body_Material_No = ""
                Bottom_Part_No = ""
                Bottom_Heat_No = ""
                Bottom_Material_No = ""
                Disc_Part_No = ""
                Disc_Heat_No = ""
                Disc_Material_No = ""
                Seat_Part_No = ""
                Seat_Heat_No = ""
                Seat_Material_No = ""
                Stem_Part_No = ""
                Stem_Heat_No = ""
                Stem_Material_No = ""
                Bray_Part_No = ""
            else:
                valve_serial_from_db = serial_data[0] or valve_serial_no  # Use parameter as fallback
                Bray_Order = serial_data[1] or ""
                Body_Part_No = serial_data[2] or ""
                Body_Heat_No = serial_data[3] or ""
                Body_Material_No = serial_data[4] or ""
                Bottom_Part_No = serial_data[5] or ""
                Bottom_Heat_No = serial_data[6] or ""
                Bottom_Material_No = serial_data[7] or ""
                Disc_Part_No = serial_data[8] or ""
                Disc_Heat_No = serial_data[9] or ""
                Disc_Material_No = serial_data[10] or ""
                Seat_Part_No = serial_data[11] or ""
                Seat_Heat_No = serial_data[12] or ""
                Seat_Material_No = serial_data[13] or ""
                Stem_Part_No = serial_data[14] or ""
                Stem_Heat_No = serial_data[15] or ""
                Stem_Material_No = serial_data[16] or ""
                assembled_by = serial_data[17] or ""
                tested_by = serial_data[18] or ""
                Bray_Part_No = serial_data[19] or ""
            
        # Fetch test results from abrs_result_status using the current valve serial number
        with connection.cursor() as cursor:
            cursor.execute(""" 
                SELECT COL1_VALUE,COL2_VALUE,COL3_VALUE,COL4_VALUE,COL5_VALUE,COL6_VALUE,COL7_VALUE,COL8_VALUE,
                       COL9_VALUE,COL10_VALUE,COL11_VALUE,COL12_VALUE,COL13_VALUE 
                FROM abrs_result_status 
                WHERE SERIAL_NO = %s 
            """, [valve_serial_no])
            
            result_data = cursor.fetchone()
            print("result data form excel report", result_data)
            
            # Get cycle test status based on station number
            if station_num == 1:
                Valve_Cycle_Test = getstatus(HmiAddress.S1_CYCLE_TEST_STATUS)
            else:  # station_num == 2
                Valve_Cycle_Test = getstatus(HmiAddress.S2_CYCLE_TEST_STATUS)
                
            if Valve_Cycle_Test == 1:
                Valve_Cycle_Test = "Yes"
            else:
                Valve_Cycle_Test = "No"
            
            if not result_data:
                print(f"[EXCEL_COPY] No test results found in abrs_result_status for valve serial: {valve_serial_no}")
                # Set default empty values
                OPEN_TORQUE = ""
                CLOSE_TORQUE = ""
                VALVE_CYCLE_TEST = ""
                HYDROSHELL_TEST_RESULT = ""
                HYDROSHELL_TEST_DURATION = ""
                HYDROSEAT_P_TEST_RESULT = ""
                HYDROSEAT_P_TEST_DURATION = ""
                HYDROSEAT_N_TEST_RESULT = ""
                HYDROSEAT_N_TEST_DURATION = ""
                AIRSEAT_P_TEST_RESULT = ""
                AIRSEAT_P_TEST_DURATION = ""
                AIRSEAT_N_TEST_RESULT = ""
                AIRSEAT_N_TEST_DURATION = ""
            else:
                OPEN_TORQUE = result_data[0] or ""
                CLOSE_TORQUE = result_data[1] or ""
                VALVE_CYCLE_TEST = Valve_Cycle_Test or ""
                HYDROSHELL_TEST_RESULT = result_data[3] or ""
                HYDROSHELL_TEST_DURATION = result_data[4] or ""
                HYDROSEAT_P_TEST_RESULT = result_data[5] or ""
                HYDROSEAT_P_TEST_DURATION = result_data[6] or ""
                HYDROSEAT_N_TEST_RESULT = result_data[7] or ""
                HYDROSEAT_N_TEST_DURATION = result_data[8] or ""
                AIRSEAT_P_TEST_RESULT = result_data[9] or ""
                AIRSEAT_P_TEST_DURATION = result_data[10] or ""
                AIRSEAT_N_TEST_RESULT = result_data[11] or ""
                AIRSEAT_N_TEST_DURATION = result_data[12] or ""

        # Load the Excel workbook to populate data
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(destination_filepath)
            worksheet = workbook.active  # Use the active sheet
            
            # Put valve serial number in cell H12
            worksheet.cell(row=12, column=8, value=valve_serial_from_db)  # H12 (row=12, column=8 for H)
            worksheet.cell(row=12, column=3, value=Bray_Order)  
            worksheet.cell(row=5, column=3, value=Body_Part_No) 
            worksheet.cell(row=5, column=6, value=Body_Heat_No) 
            worksheet.cell(row=5, column=9, value=Body_Material_No) 
            worksheet.cell(row=6, column=3, value=Bottom_Part_No) 
            worksheet.cell(row=6, column=6, value=Bottom_Heat_No) 
            worksheet.cell(row=6, column=9, value=Bottom_Material_No)
            worksheet.cell(row=7, column=3, value=Disc_Part_No) 
            worksheet.cell(row=7, column=6, value=Disc_Heat_No) 
            worksheet.cell(row=7, column=9, value=Disc_Material_No)
            worksheet.cell(row=8, column=3, value=Seat_Part_No) 
            worksheet.cell(row=8, column=6, value=Seat_Heat_No) 
            worksheet.cell(row=8, column=9, value=Seat_Material_No)
            worksheet.cell(row=9, column=3, value=Stem_Part_No) 
            worksheet.cell(row=9, column=6, value=Stem_Heat_No) 
            worksheet.cell(row=9, column=9, value=Stem_Material_No)
            worksheet.cell(row=28, column=10, value=assembled_by)
            worksheet.cell(row=29, column=10, value=tested_by)
            worksheet.cell(row=11, column=4, value=Bray_Part_No)
            worksheet.cell(row=13, column=3, value=today_date)
            worksheet.cell(row=13, column=8, value='No Leak Observed')
            
            worksheet.cell(row=16, column=10, value=OPEN_TORQUE)
            worksheet.cell(row=17, column=10, value=CLOSE_TORQUE)
            worksheet.cell(row=15, column=10, value=VALVE_CYCLE_TEST)
            worksheet.cell(row=18, column=10, value=HYDROSHELL_TEST_RESULT)
            worksheet.cell(row=19, column=10, value=HYDROSHELL_TEST_DURATION)
            worksheet.cell(row=20, column=10, value=HYDROSEAT_P_TEST_RESULT)
            worksheet.cell(row=21, column=10, value=HYDROSEAT_P_TEST_DURATION)
            worksheet.cell(row=22, column=10, value=HYDROSEAT_N_TEST_RESULT)
            worksheet.cell(row=23, column=10, value=HYDROSEAT_N_TEST_DURATION)
            worksheet.cell(row=24, column=10, value=AIRSEAT_P_TEST_RESULT)
            worksheet.cell(row=25, column=10, value=AIRSEAT_P_TEST_DURATION)
            worksheet.cell(row=26, column=10, value=AIRSEAT_N_TEST_RESULT)
            worksheet.cell(row=27, column=10, value=AIRSEAT_N_TEST_DURATION)
            

            # Save the populated workbook
            workbook.save(destination_filepath)
            workbook.close()
            
            print(f"[EXCEL_COPY] Excel template populated with valve serial '{valve_serial_from_db}' in H12: {destination_filepath}")
            
        except Exception as e:
            print(f"[EXCEL_COPY] Failed to populate Excel template: {e}")
            import traceback
            traceback.print_exc()
            print(f"[EXCEL_COPY] Excel template copied successfully (without population): {destination_filepath}")
            # Still return True as the file was copied successfully
            return True
        
        print(f"[EXCEL_COPY] Excel template copied and populated successfully: {destination_filepath}")
        return True
        
    except Exception as e:
        print(f"[EXCEL_COPY] Failed to copy Excel template: {e}")
        import traceback
        traceback.print_exc()
        return False