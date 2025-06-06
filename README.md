# Projeto Detector de Tremores Sísmicos com ESP32 e IA Embarcada (v3 - Árvore de Decisão)

## Integrantes:

* Nickolas Ferraz - RM558458
* Marcos Paolucci - RM554941
* Sandron Oliveira - RM557172
## Descrição

Este projeto implementa um sistema de detecção de tremores sísmicos utilizando um microcontrolador ESP32, um sensor acelerômetro/giroscópio MPU6050 e um modelo de Machine Learning (Árvore de Decisão) embarcado para realizar a inferência diretamente no dispositivo (Edge Computing). Quando um tremor é detectado, o ESP32 se conecta a uma rede Wi-Fi para enviar um alerta para um servidor Python central e exibe informações no Monitor Serial.

## Funcionalidades Principais

*   Leitura de dados do acelerômetro (MPU6050) pelo ESP32.
*   Taxa de amostragem configurável (atualmente 50Hz).
*   Scripts Python para coleta de dados (opcional, para gerar novos datasets), processamento, extração de features e treinamento do modelo de Árvore de Decisão.
*   Embarque dos parâmetros do scaler e da lógica da Árvore de Decisão no ESP32 para inferência local.
*   Firmware principal para o ESP32 (`firmware_v2/detector_wifi_final/detector_wifi_final.ino` - **RENOMEIE O ARQUIVO `detector_serial_v2.ino` PARA ESTE NOME**):
    *   Detecta eventos com base no modelo de Árvore de Decisão.
    *   Envia alertas via Wi-Fi para um servidor Python quando um tremor (classe 1) é detectado.
    *   Exibe o status da detecção (Tremor/Normal) e as médias dos eixos no Monitor Serial.
    *   Fornece feedback no Monitor Serial sobre o status do envio do alerta HTTP.
*   Servidor Python (`servidor_alertas_esp_v2.py`) para receber e exibir os alertas de tremor.

## Hardware Necessário

*   ESP32 (qualquer variante com Wi-Fi).
*   Sensor Acelerômetro/Giroscópio MPU6050.
*   Jumpers para conexão.
*   Cabo Micro-USB.

## Software e Bibliotecas

*   **Arduino IDE:** Para compilar e carregar o firmware no ESP32.
    *   Placa ESP32 Dev Module (ou similar) configurada na IDE.
    *   Bibliotecas Arduino (instalar via Gerenciador de Bibliotecas):
        *   `Adafruit MPU6050` (por Adafruit)
        *   `Adafruit Unified Sensor` (por Adafruit - dependência da MPU6050)
        *   `Wire` (geralmente incluída com o ESP32 core)
        *   `WiFi` (geralmente incluída com o ESP32 core)
        *   `HTTPClient` (geralmente incluída com o ESP32 core)
*   **Python 3.x:** Para os scripts de coleta, processamento e treinamento.
    *   Bibliotecas Python (instalar via `pip install -r requirements.txt` ou individualmente):
        *   `pyserial`
        *   `pandas`
        *   `numpy`
        *   `scikit-learn`
        *   `matplotlib` (se for usar o script `visualizador_tempo_real_v2.py` que foi deletado, mas pode ser útil para debug)

## Estrutura do Projeto (Atualizada)

```
gs1/
├── data/                     # Dados do projeto (para treinamento, não alterado por esta refatoração)
│   ├── raw_data/
│   ├── processed_data/
│   └── segments/
├── firmware_v2/
│   ├── detector_wifi_final/  # Firmware principal com Wi-Fi e Árvore de Decisão
│   │   └── detector_wifi_final.ino  # (Anteriormente detector_serial_v2.ino, agora com Wi-Fi)
│   └── esp32_mpu6050_data_collection/ # Firmware para coleta de dados brutos via serial
│       └── esp32_mpu6050_data_collection.ino
├── logistic_model_parameters/ # Parâmetros do scaler e regras da árvore (model_parameters.txt)
│   ├── model_parameters.txt    # Contém regras da Árvore de Decisão geradas pelo script de treino
│   ├── scaler.pkl              # Objeto Scaler salvo pelo script de treino
│   └── trained_model.pkl       # Modelo de Árvore de Decisão salvo pelo script de treino
├── scripts/                  # Scripts Python (para dataset e treino)
│   ├── marker_data_collector.py        # (original, para coleta de dados)
│   ├── extract_labeled_segments.py   # (original, para processamento)
│   ├── feature_extractor.py          # (original, para extração de features)
│   └── treinador_modelo_ia_v2.py     # (atualizado para Árvore de Decisão)
├── decision_tree_parametros/ # Pasta que você mencionou com parâmetros de árvore pré-existentes
│   ├── decision_tree_model.pkl # (Não diretamente usado pelo firmware, mas parte do seu processo)
│   ├── feature_scaler.pkl      # (Não diretamente usado pelo firmware, mas parte do seu processo)
│   └── model_params_for_c.h    # (Usado como REFERÊNCIA para a lógica da árvore no firmware)
├── servidor_alertas_esp_v2.py # Servidor Python para receber alertas Wi-Fi
└── README.md                 # Este arquivo
```

## Passos para Configuração e Uso

**1. Renomear Firmware:**
   - **IMPORTANTE:** Renomeie a pasta `firmware_v2/detector_serial_v2/` para `firmware_v2/detector_wifi_final/`.
   - Dentro desta nova pasta, renomeie o arquivo `detector_serial_v2.ino` para `detector_wifi_final.ino`.

**2. Configuração do Hardware:**
   - Conecte o MPU6050 ao ESP32 via I2C:
     - MPU6050 VCC -> ESP32 3.3V
     - MPU6050 GND -> ESP32 GND
     - MPU6050 SCL -> ESP32 GPIO22
     - MPU6050 SDA -> ESP32 GPIO21

**3. Preparação dos Scripts Python (se for treinar um novo modelo):**
   a. Se você for treinar um novo modelo de Árvore de Decisão (ou se os arquivos em `logistic_model_parameters/` não existirem ou estiverem desatualizados):
      i.  **Coleta de Dados (Opcional - se não tiver dados brutos):**
          -  Use o script `firmware_v2/esp32_mpu6050_data_collection/esp32_mpu6050_data_collection.ino` para coletar dados via serial.
          -  Execute `scripts/marker_data_collector.py` para salvar os dados brutos com marcadores (e.g., em `data/raw_data/`).
      ii. **Processamento e Extração de Features:**
          -  Execute `scripts/extract_labeled_segments.py` (requer dados em `data/raw_data/`).
          -  Execute `scripts/feature_extractor.py` (requer `data/processed_data/final_labeled_dataset.csv`).
      iii. **Treinamento do Modelo de Árvore de Decisão:**
           -  Execute `scripts/treinador_modelo_ia_v2.py`. Este script está configurado para treinar uma Árvore de Decisão.
           -  Ele salvará `scaler.pkl`, `trained_model.pkl` e `model_parameters.txt` (com as regras da árvore) na pasta `logistic_model_parameters/`.
           -  A lógica da árvore em `model_parameters.txt` deve ser verificada e, se diferente da que está no firmware, o firmware precisará ser atualizado com as novas regras.

**4. Firmware do Detector no ESP32:**
   a. Abra o sketch `firmware_v2/detector_wifi_final/detector_wifi_final.ino` na Arduino IDE.
   b. **Configure suas credenciais de Wi-Fi e o IP do servidor no arquivo `.ino`:**
      Procure pela struct `DeviceNetworkConfig networkSetup` e altere os placeholders:
      ```c++
      DeviceNetworkConfig networkSetup = {
          "SEU_WIFI_SSID_AQUI",        // <<< Altere para o SSID da sua rede Wi-Fi
          "SENHA_DO_SEU_WIFI_AQUI", // <<< Altere para a senha da sua rede Wi-Fi
          "IP_DO_SEU_SERVIDOR_PYTHON_AQUI", // <<< Altere para o IP do PC onde o servidor Python está rodando
          8081,              
          "/incoming_alert"  
      };
      ```
   c. Verifique se a lógica da Árvore de Decisão na função `classify_feature_set()` corresponde ao modelo treinado (seja o que estava no seu `model_params_for_c.h` ou um novo que você treinou e cujas regras estão em `logistic_model_parameters/model_parameters.txt`).
   d. Compile e carregue no ESP32.
   e. Abra o Monitor Serial (115200 bps) para ver o status da conexão Wi-Fi, os logs de detecção e o feedback do envio de alertas.

**5. Servidor de Alertas Python:**
   a. No seu computador, abra um terminal ou prompt de comando.
   b. Navegue até a pasta raiz do projeto (`gs1/`).
   c. Execute o servidor: `python servidor_alertas_esp_v2.py`
   d. O servidor começará a escutar na porta `8081`.
   e. Quando o ESP32 detectar um tremor e enviar o alerta HTTP, o servidor Python exibirá a mensagem no console.
   f. Certifique-se de que seu firewall permite conexões na porta especificada.

## Lógica da Árvore de Decisão no Firmware

A função `classify_feature_set()` no firmware implementa a seguinte lógica de árvore de decisão (baseada no `model_params_for_c.h` que você forneceu anteriormente):

*   **Feature Escalonada no Índice 15 (`mav_accel_y` escalada):** Se <= -0.71f:
    *   Então, verifique **Feature Escalonada no Índice 8 (`mean_accel_y` escalada):**
        *   Se <= -0.05f, a classe é `0` (Não Tremor).
        *   Se > -0.05f, a classe é `1` (Tremor).
*   Senão (Feature 15 > -0.71f), a classe é `1` (Tremor).

Se você treinar um novo modelo, as features, índices e limiares podem mudar, exigindo uma atualização manual desta função no firmware.

---
*Este README foi gerado com a assistência de IA e adaptado ao estado atual do projeto.* 