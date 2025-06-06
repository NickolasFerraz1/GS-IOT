import serial
import csv
import time
import datetime

# --- Configuration Settings ---
class DataCollectorConfig:
    SERIAL_DEVICE = 'COM3'  # MUDE AQUI para a porta serial correta do seu ESP32
    SERIAL_BAUD_RATE = 115200
    OUTPUT_CSV_FILE = 'raw_sensor_log_with_markers_refactored.csv' # Changed filename
    SERIAL_READ_TIMEOUT = 0.05 # Timeout for serial read
    CSV_FILE_HEADER = ['timestamp_pc', 'accel_x_val', 'accel_y_val', 'accel_z_val', 'esp_event_code'] # Renamed fields

def display_collection_instructions():
    config = DataCollectorConfig()
    print("\n--- Data Collection Script with Event Markers ---")
    print(f"Listening on port: {config.SERIAL_DEVICE} at {config.SERIAL_BAUD_RATE} baud")
    print(f"Saving data to: {config.OUTPUT_CSV_FILE}")
    print("Commands (type in console and press Enter):")
    print("  'b' - to mark START of an event of interest")
    print("  'e' - to mark END of an event of interest")
    print("  'q' - to QUIT script and save data")
    print("-----------------------------------------")
    print("Simulate events (tremors or non-tremors) and use 'b' and 'e' to define them.")
    print("Labeling (tremor or not) will be done in a later step.")
    print("NOTICE: Data collection briefly pauses while awaiting your command.")

def initialize_serial_port(device, baud_rate, timeout_duration):
    try:
        serial_conn = serial.Serial(device, baud_rate, timeout=timeout_duration)
        print(f"Successfully connected to {device}.")
        time.sleep(0.5)  # Allow time for ESP32 to initialize and connection to stabilize
        serial_conn.reset_input_buffer() # Clear any old data in the input buffer
        print("Serial input buffer cleared.")
        return serial_conn
    except serial.SerialException as e:
        print(f"Error opening or configuring serial port {device}: {e}")
        return None

def create_csv_output_file(filename, header_row):
    try:
        file_handle = open(filename, 'w', newline='')
        csv_data_writer = csv.writer(file_handle)
        csv_data_writer.writerow(header_row)
        print(f"File {filename} opened for writing. Data logging started.")
        return file_handle, csv_data_writer
    except IOError as e:
        print(f"Error opening or writing to CSV file {filename}: {e}")
        return None, None

def parse_sensor_data_line(data_line_str):
    if data_line_str.startswith("INFO:"):
        print(f"ESP32 Info: {data_line_str}")
        return "info" # Special type for info lines
    if not data_line_str: # Ignore completely empty lines
        return None

    parts = data_line_str.split(',')
    if len(parts) == 4: # Expected format: Ax, Ay, Az, EventMarkerFromESP
        try:
            pc_timestamp = datetime.datetime.now().isoformat()
            ax = float(parts[0])
            ay = float(parts[1])
            az = float(parts[2])
            event_marker = int(parts[3])
            return [pc_timestamp, ax, ay, az, event_marker]
        except ValueError:
            if data_line_str: # Only print warning if the malformed line wasn't empty
                 print(f"Warning: Value conversion error for data line: '{data_line_str}'")
            return None
    else: # Lines with unexpected format
        if data_line_str:
           print(f"Warning: Unexpected line format: '{data_line_str}'")
        return None

def process_incoming_esp_data(active_serial_conn, data_writer):
    lines_processed_count = 0
    if not active_serial_conn or not data_writer:
        return lines_processed_count

    while active_serial_conn.in_waiting > 0:
        try:
            raw_line_bytes = active_serial_conn.readline()
            line_as_string = raw_line_bytes.decode('utf-8').strip()
            
            parsed_data = parse_sensor_data_line(line_as_string)
            
            if parsed_data and parsed_data != "info":
                data_writer.writerow(parsed_data)
                lines_processed_count += 1
            
        except UnicodeDecodeError:
            # print("Warning: Unicode decode error from serial.") # Optionally log
            pass # Silently ignore for now
        except Exception as e:
            print(f"Error reading/processing serial line: {e}")
    return lines_processed_count

def handle_user_input_commands(active_serial_conn):
    try:
        command_input = input("Enter command (b, e, q): ").strip().lower()
        if command_input == 'b':
            active_serial_conn.write(b'b')
            print("-> Command 'b' (START event) sent to ESP32.")
        elif command_input == 'e':
            active_serial_conn.write(b'e')
            print("-> Command 'e' (END event) sent to ESP32.")
        elif command_input == 'q':
            print("Command 'q' (QUIT) received. Exiting loop...")
            return False # Signal to stop collection
        elif command_input: # User typed something invalid
            print(f"Unknown command '{command_input}'. Use 'b', 'e', or 'q'.")
        # If user just presses Enter (empty input), continue loop
        return True # Signal to continue collection
    except EOFError:
        print("End of input stream (EOF). Exiting...")
        return False # Signal to stop collection

def perform_data_collection_workflow():
    display_collection_instructions()
    config = DataCollectorConfig()
    
    serial_port_connection = None
    output_csv_file = None
    
    try:
        serial_port_connection = initialize_serial_port(
            config.SERIAL_DEVICE, 
            config.SERIAL_BAUD_RATE, 
            config.SERIAL_READ_TIMEOUT
        )
        if not serial_port_connection:
            print("Failed to initialize serial port. Exiting.")
            return

        output_csv_file, csv_file_writer = create_csv_output_file(
            config.OUTPUT_CSV_FILE, 
            config.CSV_FILE_HEADER
        )
        if not output_csv_file or not csv_file_writer:
            print("Failed to create CSV output file. Exiting.")
            return

        print("\nType 'b' for START of event, 'e' for END of event, 'q' to QUIT.")
        
        is_collecting = True
        while is_collecting:
            # Prioritize processing all available data from ESP32
            process_incoming_esp_data(serial_port_connection, csv_file_writer)
            
            # Then, wait for user command
            is_collecting = handle_user_input_commands(serial_port_connection)
            
    except KeyboardInterrupt:
        print("\nCollection interrupted by user (Ctrl+C).")
    except Exception as general_exception:
        print(f"An unexpected general error occurred: {general_exception}")
    finally:
        if serial_port_connection and serial_port_connection.is_open:
            serial_port_connection.close()
            print("Serial port closed.")
        if output_csv_file:
            output_csv_file.close()
            # No need to explicitly close csv_file_writer if file_handle is closed
        print(f"Data collection process finished. Check the file '{config.OUTPUT_CSV_FILE}'.")

if __name__ == '__main__':
    perform_data_collection_workflow()