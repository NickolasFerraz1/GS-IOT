import pandas as pd
import numpy as np

# --- Configuration for Feature Extraction ---
class FeatureExtractorConfig:
    # Input CSV from the refactored segment extraction script
    SOURCE_LABELED_DATA_CSV = 'master_feature_ready_dataset.csv' 
    # Output CSV for the training script
    FINAL_FEATURES_CSV = 'final_ml_training_features.csv'

    # Windowing parameters for feature extraction
    WINDOW_DURATION_SAMPLES = 50  # Number of samples per window
    SLIDE_STEP_SAMPLES = 25       # Step size for sliding window (overlap if < WINDOW_DURATION_SAMPLES)

    # Column names expected in the input CSV (must align with extract_labeled_segments_refactored.py output)
    ACCEL_X_COL = 'accel_x_val'
    ACCEL_Y_COL = 'accel_y_val'
    ACCEL_Z_COL = 'accel_z_val'
    LABEL_COL = 'label'
    
    # List of sensor axes columns for iteration
    SENSOR_AXES_COLS = [ACCEL_X_COL, ACCEL_Y_COL, ACCEL_Z_COL]

class FeatureEngineeringPipeline:
    def __init__(self, fe_config):
        self.config = fe_config
        self.generated_feature_names = [] # To store the order of feature columns

    def _calculate_statistical_features(self, data_series, feature_prefix):
        """Helper to compute a standard set of statistical features for a data series."""
        features = {}
        features[f'{feature_prefix}_mean'] = np.mean(data_series)
        features[f'{feature_prefix}_std_dev'] = np.std(data_series)
        features[f'{feature_prefix}_variance'] = np.var(data_series)
        features[f'{feature_prefix}_min_val'] = np.min(data_series)
        features[f'{feature_prefix}_max_val'] = np.max(data_series)
        features[f'{feature_prefix}_range_val'] = np.ptp(data_series) # Peak-to-peak
        features[f'{feature_prefix}_energy_sum'] = np.sum(data_series**2)
        features[f'{feature_prefix}_mean_abs_dev'] = np.mean(np.abs(data_series - np.mean(data_series))) # Mean Absolute Deviation
        return features

    def _compute_features_for_window(self, data_window_df):
        """Computes all features for a single window DataFrame."""
        window_features_map = {}

        # Features for each accelerometer axis
        for axis_column_name in self.config.SENSOR_AXES_COLS:
            sensor_axis_data = data_window_df[axis_column_name]
            # Deriving a short prefix like 'x' from 'accel_x_val'
            prefix = axis_column_name.split('_')[1] 
            window_features_map.update(self._calculate_statistical_features(sensor_axis_data, prefix))

        # Features for Signal Vector Magnitude (SVM)
        svm_values = np.sqrt(
            data_window_df[self.config.ACCEL_X_COL]**2 +
            data_window_df[self.config.ACCEL_Y_COL]**2 +
            data_window_df[self.config.ACCEL_Z_COL]**2
        )
        window_features_map.update(self._calculate_statistical_features(svm_values, 'svm'))
        
        # Add label from the window
        if self.config.LABEL_COL in data_window_df.columns:
            if data_window_df[self.config.LABEL_COL].nunique() == 1:
                window_features_map[self.config.LABEL_COL] = data_window_df[self.config.LABEL_COL].iloc[0]
            else:
                print(f"Warning: Window at (index approx {data_window_df.index[0]}) has mixed labels. Using first label.")
                window_features_map[self.config.LABEL_COL] = data_window_df[self.config.LABEL_COL].iloc[0]
        else:
            print(f"Warning: Label column '{self.config.LABEL_COL}' not found in window. Assigning -1.")
            window_features_map[self.config.LABEL_COL] = -1 
            
        # Store feature names in order if not already done (from the first window processed)
        if not self.generated_feature_names:
             self.generated_feature_names = list(window_features_map.keys())

        return window_features_map

    def _load_input_dataset(self):
        """Loads the labeled dataset from the CSV file specified in config."""
        try:
            dataset_df = pd.read_csv(self.config.SOURCE_LABELED_DATA_CSV)
            print(f"Successfully loaded source data: '{self.config.SOURCE_LABELED_DATA_CSV}' (Rows: {len(dataset_df)})")
            
            # Validate required columns
            required_cols = self.config.SENSOR_AXES_COLS + [self.config.LABEL_COL]
            for col in required_cols:
                if col not in dataset_df.columns:
                    print(f"CRITICAL ERROR: Required column '{col}' is missing from the input CSV.")
                    return None
            return dataset_df
        except FileNotFoundError:
            print(f"CRITICAL ERROR: Input data file not found: '{self.config.SOURCE_LABELED_DATA_CSV}'")
            print("Ensure 'extract_labeled_segments.py' (refactored) was run successfully.")
            return None
        except Exception as e:
            print(f"CRITICAL ERROR during CSV read ('{self.config.SOURCE_LABELED_DATA_CSV}'): {e}")
            return None

    def _save_feature_set_to_csv(self, final_features_df):
        """Saves the DataFrame of extracted features to a CSV file."""
        # Ensure label column is the last one, for convention
        if self.config.LABEL_COL in final_features_df.columns and final_features_df.columns[-1] != self.config.LABEL_COL:
            label_data_column = final_features_df.pop(self.config.LABEL_COL)
            final_features_df[self.config.LABEL_COL] = label_data_column
        
        final_features_df.to_csv(self.config.FINAL_FEATURES_CSV, index=False)
        print(f"\nFeature dataset saved to: '{self.config.FINAL_FEATURES_CSV}' ({len(final_features_df)} windows generated)")
        print(f"Number of columns (features + label): {len(final_features_df.columns)}")
        # print(f"Feature column names: {list(final_features_df.columns)}")

    def run_feature_generation(self):
        """Main orchestration method for the feature engineering pipeline."""
        print("--- Initiating Feature Engineering Pipeline ---")
        input_df = self._load_input_dataset()

        if input_df is None:
            print("Pipeline terminated due to issues loading input data.")
            return

        # Create a temporary 'event_block_id' to process windows only within continuous segments of the same label
        input_df['event_block_id'] = (input_df[self.config.LABEL_COL] != input_df[self.config.LABEL_COL].shift()).cumsum()
        
        extracted_features_list = []
        num_event_blocks = input_df['event_block_id'].nunique()
        print(f"Data contains {num_event_blocks} distinct event blocks to process for windowing.")

        for block_id, block_df in input_df.groupby('event_block_id'):
            # print(f"Processing block ID: {block_id} ({len(block_df)} rows)") # For debugging
            start_offset = 0
            while start_offset + self.config.WINDOW_DURATION_SAMPLES <= len(block_df):
                window_data = block_df.iloc[start_offset : start_offset + self.config.WINDOW_DURATION_SAMPLES]
                
                if len(window_data) == self.config.WINDOW_DURATION_SAMPLES: # Ensure full window
                    features_for_current_window = self._compute_features_for_window(window_data)
                    extracted_features_list.append(features_for_current_window)
                
                start_offset += self.config.SLIDE_STEP_SAMPLES

        if not extracted_features_list:
            print("ALERT: No features were extracted from the data.")
            print("Check window size, step size settings, and the length of continuous data segments.")
            if num_event_blocks > 0:
                 print(f"Event blocks were identified, but might have been too short for window size: {self.config.WINDOW_DURATION_SAMPLES}.")
            return

        # Create DataFrame using the stored order of feature names for consistency
        output_features_df = pd.DataFrame(extracted_features_list, columns=self.generated_feature_names)
        self._save_feature_set_to_csv(output_features_df)
        print("--- Feature Engineering Pipeline Successfully Completed ---")

def execute_feature_extraction_workflow(): # Renamed main function
    print("Initializing Feature Extraction Workflow...")
    # Inform user about dependencies, though they are standard for data science
    # print("This script requires pandas and numpy libraries.") 
    
    pipeline_config = FeatureExtractorConfig()
    feature_pipeline_instance = FeatureEngineeringPipeline(pipeline_config)
    feature_pipeline_instance.run_feature_generation()

if __name__ == '__main__':
    execute_feature_extraction_workflow() 