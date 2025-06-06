#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h>
#include <WiFi.h>        // Adicionado para Wi-Fi
#include <HTTPClient.h>  // Adicionado para HTTP Client

// --- Configuration Structures ---
struct DetectorConfig { // Renomeado de globalDetectorConfig para evitar conflito com a struct de rede
    const int SAMPLES_PER_WINDOW;
    const int TARGET_SAMPLING_HZ;
    const int SAMPLING_INTERVAL_MS;
};

struct DeviceNetworkConfig {
    const char* targetSsid;
    const char* wifiPassword;
    const char* backendServerIp;
    int backendServerPort;
    const char* alertEndpoint;
    String fullServerUrlBase; 
};

// --- Global Detector Configuration ---
DetectorConfig sensorProcessingConfig = { // Nome da instância alterado
    50,  // SAMPLES_PER_WINDOW
    50,  // TARGET_SAMPLING_HZ
    1000 / 50 // SAMPLING_INTERVAL_MS
};

// --- Network Configuration ---
DeviceNetworkConfig networkSetup = {
    "FIAP-IOT",        // <<< ALTERE AQUI
    "F!@p25.IOT", // <<< ALTERE AQUI
    "172.22.0.7",      // <<< ALTERE AQUI
    8081,              
    "/incoming_alert"  
};

// MPU6050 Sensor Instance
Adafruit_MPU6050 motionSensor;

// Data Buffers for Windowing
float input_window_ax[50]; 
float input_window_ay[50];
float input_window_az[50];
float input_window_svm[50]; 
int window_fill_idx = 0;    

// --- Embedded Model & Scaler Parameters ---
const int DETECTOR_MODEL_FEATURE_COUNT = 32;
const float detector_scaler_means[DETECTOR_MODEL_FEATURE_COUNT] = {10.21886541f, 2.28296651f, 10.20023889f, 5.22562478f, 18.98728822f, 13.76166343f, 5740.88572806f, 10.23268411f, 0.29410218f, 0.93116674f, 1.66920908f, -1.65741119f, 3.62482139f, 5.28223258f, 89.91796834f, 0.71845937f, -2.25340990f, 1.24075164f, 2.92679911f, -6.87506484f, 0.91182524f, 7.78689007f, 404.03677510f, 2.41622221f, 10.64256298f, 2.36730343f, 11.20050337f, 6.55009465f, 20.43635561f, 13.88626096f, 6234.84047149f, 10.64256298f};
const float detector_scaler_scales[DETECTOR_MODEL_FEATURE_COUNT] = {0.43848090f, 2.23345087f, 13.37981538f, 4.70485023f, 9.60728868f, 13.52942530f, 904.70063484f, 0.43511866f, 0.20652894f, 0.89562134f, 2.23530918f, 1.66032869f, 3.86593248f, 5.19538032f, 119.17124595f, 0.49746271f, 0.27582642f, 1.17785164f, 3.80559178f, 5.26900775f, 3.13734484f, 7.75847094f, 212.97004625f, 0.27281179f, 0.48182907f, 2.36566647f, 15.45066859f, 3.43805079f, 11.08204307f, 13.91323103f, 1188.02728350f, 0.48182907f};

float calculated_feature_set[DETECTOR_MODEL_FEATURE_COUNT];

// --- WiFi Connection Function (Adicionada) ---
void connectToWiFiNetwork() { 
    delay(20); 
    WiFi.begin(networkSetup.targetSsid, networkSetup.wifiPassword);
    int connection_attempts = 0;
    while (WiFi.status() != WL_CONNECTED && connection_attempts < 25) {
        delay(500);
        connection_attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        networkSetup.fullServerUrlBase = "http://" + String(networkSetup.backendServerIp) + ":" + String(networkSetup.backendServerPort);
        Serial.println("WiFi Conectado. IP: " + WiFi.localIP().toString());
    } else {
        Serial.println("Falha ao conectar WiFi.");
    }
}

// --- HTTP Alert Dispatch Function (Modificada para feedback) ---
void dispatchTremorNotificationHTTP(String eventDescription) { 
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient httpClient; 
        String complete_server_url = networkSetup.fullServerUrlBase + String(networkSetup.alertEndpoint) + "?event_type=" + eventDescription;
        
        // Serial.print("Enviando alerta para: "); // Opcional, pode ser removido se quiser menos prints
        // Serial.println(complete_server_url);

        httpClient.begin(complete_server_url.c_str());
        int http_response_code = httpClient.GET();

        if (http_response_code > 0) {
            // String server_response_payload = httpClient.getString(); // Payload não é necessário para este feedback
            if (http_response_code == HTTP_CODE_OK) { // HTTP_CODE_OK é geralmente 200
                 Serial.println("  -> Alerta enviado ao servidor com sucesso.");
            } else {
                 Serial.print("  -> Alerta enviado, resposta do servidor: HTTP ");
                 Serial.println(http_response_code);
            }
        } else {
            Serial.print("  -> Falha ao enviar alerta. Erro HTTP: ");
            Serial.println(httpClient.errorToString(http_response_code).c_str());
        }
        httpClient.end();
    } else {
        Serial.println("  -> Falha no envio: WiFi desconectado.");
    }
}

// --- Mathematical Utility Functions for Feature Calculation (Mantidas como estavam) ---
float compute_mean_from_buffer(float buffer[], int count) {
    if (count == 0) return 0.0f;
    float total_sum = 0.0f;
    for (int i = 0; i < count; i++) total_sum += buffer[i];
    return total_sum / count;
}

float compute_std_dev_from_buffer(float buffer[], int count, float buffer_mean) {
    if (count == 0) return 0.0f;
    float sum_sq_diffs = 0.0f;
    for (int i = 0; i < count; i++) {
        sum_sq_diffs += powf(buffer[i] - buffer_mean, 2);
    }
    return sqrtf(sum_sq_diffs / count);
}

float find_min_in_buffer(float buffer[], int count) {
    if (count == 0) return 0.0f; 
    float min_observed = buffer[0];
    for (int i = 1; i < count; i++) {
        if (buffer[i] < min_observed) min_observed = buffer[i];
    }
    return min_observed;
}

float find_max_in_buffer(float buffer[], int count) {
    if (count == 0) return 0.0f; 
    float max_observed = buffer[0];
    for (int i = 1; i < count; i++) {
        if (buffer[i] > max_observed) max_observed = buffer[i];
    }
    return max_observed;
}

float compute_energy_from_buffer(float buffer[], int count) {
    float energy_sum_sq = 0.0f;
    for (int i = 0; i < count; i++) {
        energy_sum_sq += powf(buffer[i], 2);
    }
    return energy_sum_sq;
}

float compute_mav_from_buffer(float buffer[], int count) { 
    if (count == 0) return 0.0f;
    float sum_abs_values = 0.0f;
    for (int i = 0; i < count; i++) {
        sum_abs_values += fabsf(buffer[i]);
    }
    return sum_abs_values / count;
}

// --- Core Feature Derivation Function (Mantida como estava) ---
void derive_features_from_sample_window() { 
    for (int i = 0; i < sensorProcessingConfig.SAMPLES_PER_WINDOW; i++) {
        input_window_svm[i] = sqrtf(powf(input_window_ax[i], 2) + powf(input_window_ay[i], 2) + powf(input_window_az[i], 2));
    }
    float* data_input_streams[] = {input_window_ax, input_window_ay, input_window_az, input_window_svm};
    int current_feature_write_idx = 0; 
    for (int stream_idx = 0; stream_idx < 4; ++stream_idx) {
        float* active_data_stream = data_input_streams[stream_idx];
        float stream_mean = compute_mean_from_buffer(active_data_stream, sensorProcessingConfig.SAMPLES_PER_WINDOW);
        float stream_std_dev = compute_std_dev_from_buffer(active_data_stream, sensorProcessingConfig.SAMPLES_PER_WINDOW, stream_mean);
        float stream_variance = powf(stream_std_dev, 2);
        float stream_min = find_min_in_buffer(active_data_stream, sensorProcessingConfig.SAMPLES_PER_WINDOW);
        float stream_max = find_max_in_buffer(active_data_stream, sensorProcessingConfig.SAMPLES_PER_WINDOW);
        float stream_ptp = stream_max - stream_min; 
        float stream_energy = compute_energy_from_buffer(active_data_stream, sensorProcessingConfig.SAMPLES_PER_WINDOW);
        float stream_mav = compute_mav_from_buffer(active_data_stream, sensorProcessingConfig.SAMPLES_PER_WINDOW);
        calculated_feature_set[current_feature_write_idx++] = stream_mean;
        calculated_feature_set[current_feature_write_idx++] = stream_std_dev;
        calculated_feature_set[current_feature_write_idx++] = stream_variance;
        calculated_feature_set[current_feature_write_idx++] = stream_min;
        calculated_feature_set[current_feature_write_idx++] = stream_max;
        calculated_feature_set[current_feature_write_idx++] = stream_ptp;
        calculated_feature_set[current_feature_write_idx++] = stream_energy;
        calculated_feature_set[current_feature_write_idx++] = stream_mav;
    }
}

// --- Feature Standardization Function (Mantida como estava) ---
void normalize_derived_features() { 
    for (int i = 0; i < DETECTOR_MODEL_FEATURE_COUNT; i++) {
        if (detector_scaler_scales[i] == 0) { 
            calculated_feature_set[i] = (calculated_feature_set[i] - detector_scaler_means[i]);
        } else {
            calculated_feature_set[i] = (calculated_feature_set[i] - detector_scaler_means[i]) / detector_scaler_scales[i];
        }
    }
}

// --- Model Inference Function (Decision Tree) (Mantida como estava) ---
int classify_feature_set() { 
    if (calculated_feature_set[15] <= -0.71f) {
        if (calculated_feature_set[8] <= -0.05f) {
            return 0; // Classe 0
        } else {
            return 1; // Classe 1
        }
    } else {
        return 1; // Classe 1
    }
}

// --- Initialization Sub-routines ---
void initSerialComm() {
    Serial.begin(115200);
    unsigned long startTime = millis();
    while (!Serial && (millis() - startTime < 2000)) { 
        delay(10);
    }
    // Serial.println("\nESP32 Seismic Detector (WiFi Version) - Initializing Systems..."); // Modificado
}

void initMotionSensor() {
    if (!motionSensor.begin()) { 
        Serial.println("FATAL: MPU6050 Error");
        while (1) { delay(100); } 
    }
    motionSensor.setAccelerometerRange(MPU6050_RANGE_8_G); 
    motionSensor.setGyroRange(MPU6050_RANGE_500_DEG);
    motionSensor.setFilterBandwidth(MPU6050_BAND_21_HZ);
    delay(100);
}

// --- Main Arduino Setup Function (Modificada) ---
void setup() {
    initSerialComm();
    Serial.println("\n--- Detector de Tremores ESP32 com WiFi V3 ---"); // Nova mensagem de título
    initMotionSensor();
    connectToWiFiNetwork(); // Adicionada conexão Wi-Fi
    Serial.println("Sistema pronto.");
}

// --- Main Arduino Loop Function (Modificada) ---
void loop() {
    sensors_event_t accel_event, gyro_event, temp_event; 
    motionSensor.getEvent(&accel_event, &gyro_event, &temp_event);

    input_window_ax[window_fill_idx] = accel_event.acceleration.x;
    input_window_ay[window_fill_idx] = accel_event.acceleration.y;
    input_window_az[window_fill_idx] = accel_event.acceleration.z;
    window_fill_idx++;

    if (window_fill_idx >= sensorProcessingConfig.SAMPLES_PER_WINDOW) {
        derive_features_from_sample_window();
        normalize_derived_features();
        int prediction_result = classify_feature_set();

        if (prediction_result == 1) { 
            Serial.print("ALERT: Tremor! AX:");
            Serial.print(compute_mean_from_buffer(input_window_ax, sensorProcessingConfig.SAMPLES_PER_WINDOW), 2);
            Serial.print(" AY:");
            Serial.print(compute_mean_from_buffer(input_window_ay, sensorProcessingConfig.SAMPLES_PER_WINDOW), 2);
            Serial.print(" AZ:");
            Serial.println(compute_mean_from_buffer(input_window_az, sensorProcessingConfig.SAMPLES_PER_WINDOW), 2);
            dispatchTremorNotificationHTTP("TremorDetected_DT_V3"); // Sufixo atualizado 
        } else {
            Serial.print("Status: Normal. AX:");
            Serial.print(compute_mean_from_buffer(input_window_ax, sensorProcessingConfig.SAMPLES_PER_WINDOW), 2);
            Serial.print(" AY:");
            Serial.print(compute_mean_from_buffer(input_window_ay, sensorProcessingConfig.SAMPLES_PER_WINDOW), 2);
            Serial.print(" AZ:");
            Serial.println(compute_mean_from_buffer(input_window_az, sensorProcessingConfig.SAMPLES_PER_WINDOW), 2);
        }
        window_fill_idx = 0; 
    }
    delay(sensorProcessingConfig.SAMPLING_INTERVAL_MS);
} 