// --- Parâmetros do Modelo (Árvore de Decisão) e Scaler para Implementação em C/C++ ---
// Gerado em: 2025-06-05 00:48:56.958139

// Parâmetros do StandardScaler (média e escala/desvio_padrão):
// Use estes para escalar as features de entrada na sua aplicação C/C++ antes da predição.
// Número de features esperado pelo scaler: 32
// Nomes das features (na ordem esperada pelo scaler/modelo):
// Feature 0: mean_accel_x
// Feature 1: std_accel_x
// Feature 2: var_accel_x
// Feature 3: min_accel_x
// Feature 4: max_accel_x
// Feature 5: ptp_accel_x
// Feature 6: energy_accel_x
// Feature 7: mav_accel_x
// Feature 8: mean_accel_y
// Feature 9: std_accel_y
// Feature 10: var_accel_y
// Feature 11: min_accel_y
// Feature 12: max_accel_y
// Feature 13: ptp_accel_y
// Feature 14: energy_accel_y
// Feature 15: mav_accel_y
// Feature 16: mean_accel_z
// Feature 17: std_accel_z
// Feature 18: var_accel_z
// Feature 19: min_accel_z
// Feature 20: max_accel_z
// Feature 21: ptp_accel_z
// Feature 22: energy_accel_z
// Feature 23: mav_accel_z
// Feature 24: mean_svm
// Feature 25: std_svm
// Feature 26: var_svm
// Feature 27: min_svm
// Feature 28: max_svm
// Feature 29: ptp_svm
// Feature 30: energy_svm
// Feature 31: mav_svm
const float SCALER_MEANS[] = {10.21886541f, 2.28296651f, 10.20023889f, 5.22562478f, 18.98728822f, 13.76166343f, 5740.88572806f, 10.23268411f, 0.29410218f, 0.93116674f, 1.66920908f, -1.65741119f, 3.62482139f, 5.28223258f, 89.91796834f, 0.71845937f, -2.25340990f, 1.24075164f, 2.92679911f, -6.87506484f, 0.91182524f, 7.78689007f, 404.03677510f, 2.41622221f, 10.64256298f, 2.36730343f, 11.20050337f, 6.55009465f, 20.43635561f, 13.88626096f, 6234.84047149f, 10.64256298f};

const float SCALER_SCALES[] = {0.43848090f, 2.23345087f, 13.37981538f, 4.70485023f, 9.60728868f, 13.52942530f, 904.70063484f, 0.43511866f, 0.20652894f, 0.89562134f, 2.23530918f, 1.66032869f, 3.86593248f, 5.19538032f, 119.17124595f, 0.49746271f, 0.27582642f, 1.17785164f, 3.80559178f, 5.26900775f, 3.13734484f, 7.75847094f, 212.97004625f, 0.27281179f, 0.48182907f, 2.36566647f, 15.45066859f, 3.43805079f, 11.08204307f, 13.91323103f, 1188.02728350f, 0.48182907f};

// Regras da Árvore de Decisão:
// A exportação direta de uma árvore para C geralmente envolve a implementação de lógica if/else.
// A representação de texto abaixo pode ajudar a guiar a implementação manual.
// Use isso como referência para traduzir manualmente a estrutura da árvore.
/*
|--- mav_accel_y <= -0.71
|   |--- mean_accel_y <= -0.05
|   |   |--- class: 0
|   |--- mean_accel_y >  -0.05
|   |   |--- class: 1
|--- mav_accel_y >  -0.71
|   |--- class: 1
*/
