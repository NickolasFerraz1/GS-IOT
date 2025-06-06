import os
import pandas as pd

# --- Configuration for Segment Extraction ---
class ExtractionConfig:
    # Input files from the data collector (assuming refactored names)
    NO_TREMOR_SOURCE_FILE = 'raw_sensor_log_with_markers_refactored_0.csv' # Example: ensure this matches output of collector for non-tremor
    TREMOR_SOURCE_FILE = 'raw_sensor_log_with_markers_refactored_1.csv'    # Example: ensure this matches output of collector for tremor

    # Output directories and final file
    BASE_SEGMENT_OUTPUT_DIR = 'extracted_data_segments' # Renamed
    # Subdirectory names will be generated (e.g., 'no_tremor_segments', 'tremor_segments')
    FINAL_LABELED_DATASET_FILENAME = 'master_feature_ready_dataset.csv' # Renamed

    # Column names (must match CSV from refactored marker_data_collector.py)
    TIMESTAMP_COLUMN = 'timestamp_pc'
    ACCEL_X_COLUMN = 'accel_x_val'
    ACCEL_Y_COLUMN = 'accel_y_val'
    ACCEL_Z_COLUMN = 'accel_z_val'
    EVENT_MARKER_COLUMN = 'esp_event_code' # Renamed from 'event_marker_from_esp32'
    
    COLUMNS_FOR_INDIVIDUAL_SEGMENTS = [TIMESTAMP_COLUMN, ACCEL_X_COLUMN, ACCEL_Y_COLUMN, ACCEL_Z_COLUMN]

    # Event markers (as defined in ESP32/collector)
    MARKER_FOR_EVENT_START = 1
    MARKER_FOR_EVENT_END = 2

    # Labels to assign
    LABEL_FOR_NO_TREMOR = 0
    LABEL_FOR_TREMOR = 1

class SegmentProcessor:
    def __init__(self, config_obj):
        self.config = config_obj
        self.output_dir_no_tremor = os.path.join(self.config.BASE_SEGMENT_OUTPUT_DIR, 'no_tremor_events')
        self.output_dir_tremor = os.path.join(self.config.BASE_SEGMENT_OUTPUT_DIR, 'tremor_events')
        self._create_output_directories()

    def _ensure_dir_exists(self, dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Directory successfully created: {dir_path}")

    def _create_output_directories(self):
        self._ensure_dir_exists(self.config.BASE_SEGMENT_OUTPUT_DIR)
        self._ensure_dir_exists(self.output_dir_no_tremor)
        self._ensure_dir_exists(self.output_dir_tremor)

    def _save_segment_to_file(self, segment_dataframe, output_path, event_label, segment_num):
        # Using a more descriptive filename format
        filename = f"event_class_{event_label}_segment_{segment_num:04d}.csv"
        full_path = os.path.join(output_path, filename)
        
        # Select only the desired columns for individual segment files
        data_to_save = segment_dataframe[self.config.COLUMNS_FOR_INDIVIDUAL_SEGMENTS].copy()
        
        data_to_save.to_csv(full_path, index=False)
        print(f"  Segment {segment_num} (label {event_label}) saved: {full_path} ({len(data_to_save)} rows)")

    def _extract_segments_from_single_file(self, input_csv_filepath, assigned_label, segments_output_dir):
        print(f"\nProcessing source file: {input_csv_filepath} with assigned label: {assigned_label}")
        collected_segments_dfs = []
        segment_serial_number = 0

        try:
            source_df = pd.read_csv(input_csv_filepath)
        except FileNotFoundError:
            print(f"ERROR: Input CSV file not found: {input_csv_filepath}")
            return collected_segments_dfs
        except pd.errors.EmptyDataError:
            print(f"WARNING: Input CSV file is empty: {input_csv_filepath}")
            return collected_segments_dfs
        except Exception as e:
            print(f"ERROR reading {input_csv_filepath}: {e}")
            return collected_segments_dfs

        if self.config.EVENT_MARKER_COLUMN not in source_df.columns:
            print(f"ERROR: Event marker column '{self.config.EVENT_MARKER_COLUMN}' not found in {input_csv_filepath}.")
            return collected_segments_dfs

        currently_in_event = False
        segment_start_index_val = -1

        for idx, table_row in source_df.iterrows():
            marker_value = table_row[self.config.EVENT_MARKER_COLUMN]

            if marker_value == self.config.MARKER_FOR_EVENT_START:
                if currently_in_event:
                    print(f"Warning in {input_csv_filepath} [row {idx+2}]: New START marker found within an active event. Previous start is overridden.")
                segment_start_index_val = idx
                currently_in_event = True
            
            elif marker_value == self.config.MARKER_FOR_EVENT_END:
                if currently_in_event:
                    # Extract segment including the end marker row
                    current_segment_df = source_df.iloc[segment_start_index_val : idx + 1].copy()
                    
                    if not current_segment_df.empty:
                        segment_serial_number += 1
                        self._save_segment_to_file(current_segment_df, segments_output_dir, assigned_label, segment_serial_number)
                        
                        # Add label column for the final aggregated dataset
                        current_segment_df['label'] = assigned_label
                        # Select columns for the final dataset (data + label)
                        cols_for_master_dataset = self.config.COLUMNS_FOR_INDIVIDUAL_SEGMENTS + ['label']
                        collected_segments_dfs.append(current_segment_df[cols_for_master_dataset])
                    else:
                        print(f"Warning in {input_csv_filepath} [row {idx+2}]: Empty segment detected and ignored.")
                    
                    currently_in_event = False
                    segment_start_index_val = -1 
                else:
                    print(f"Warning in {input_csv_filepath} [row {idx+2}]: END marker found without a preceding START marker. Ignoring.")
        
        if currently_in_event:
            print(f"Warning for {input_csv_filepath}: File ended while an event was still active (START marker without corresponding END). This final partial segment was not saved.")

        print(f"Completed processing for {input_csv_filepath}. Total segments extracted: {segment_serial_number}.")
        return collected_segments_dfs

    def run_extraction_pipeline(self):
        print("--- Commencing Segment Extraction and Labeling Pipeline ---")

        segments_no_tremor_list = self._extract_segments_from_single_file(
            self.config.NO_TREMOR_SOURCE_FILE, 
            self.config.LABEL_FOR_NO_TREMOR, 
            self.output_dir_no_tremor
        )
        
        segments_tremor_list = self._extract_segments_from_single_file(
            self.config.TREMOR_SOURCE_FILE, 
            self.config.LABEL_FOR_TREMOR, 
            self.output_dir_tremor
        )

        all_extracted_data = segments_no_tremor_list + segments_tremor_list

        if not all_extracted_data:
            print("\nNo segments were extracted from any source files. The final combined dataset cannot be created.")
            print("Please verify input files and marker consistency.")
            return

        master_dataset_df = pd.concat(all_extracted_data, ignore_index=True)
        
        # Optional: Sort by timestamp if global chronological order is desired
        # master_dataset_df = master_dataset_df.sort_values(by=self.config.TIMESTAMP_COLUMN).reset_index(drop=True)
        
        master_dataset_df.to_csv(self.config.FINAL_LABELED_DATASET_FILENAME, index=False)
        print(f"\nFinal combined and labeled dataset saved as: {self.config.FINAL_LABELED_DATASET_FILENAME} ({len(master_dataset_df)} total rows)")
        print(f"Columns in the final dataset: {list(master_dataset_df.columns)}")
        print("--- Pipeline execution completed. ---")

def execute_segmentation_script():
    print("Initializing Segment Extraction Utility...")
    # It's good practice to inform the user about dependencies like pandas.
    # print("Ensure 'pandas' library is installed (pip install pandas).") 
    
    configuration = ExtractionConfig()
    processor_instance = SegmentProcessor(configuration)
    processor_instance.run_extraction_pipeline()

if __name__ == '__main__':
    execute_segmentation_script() 