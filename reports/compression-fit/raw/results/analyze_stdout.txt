### A. Quality, compression and latency per family (local; n items per family in header)

**qa** (n=40 items, 9 arms, same prompts, llama3.2:3b on CPU)

| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s |
|---|---|---|---|---|---|---|---|---|---|
| uncompressed | 1.000 [0.912, 1.000] | - | - | 1.00x | 1.00x | 10.59 [10.03, 11.24] | 13.27 [11.97, 14.16] | 0.00/0.00 | 0.00 |
| LLMLingua-2 (~2x) | 0.750 [0.598, 0.858] | -0.250 [-0.400, -0.125] | 0.002 | 2.37x | 1.81x | 7.22 [6.87, 7.69] | 8.47 [8.09, 10.19] | 0.89/1.37 | 3.38 |
| LLMLingua-2 (~3x) | 0.625 [0.470, 0.758] | -0.375 [-0.525, -0.225] | <0.001 | 3.16x | 2.12x | 6.50 [6.32, 7.00] | 8.72 [7.37, 10.09] | 0.91/1.77 | 3.37 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.725 [0.572, 0.839] | -0.275 [-0.425, -0.150] | 0.001 | 2.34x | 1.79x | 7.51 [7.28, 7.83] | 10.29 [8.35, 11.45] | 0.78/0.87 | 3.13 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.950 [0.835, 0.986] | -0.050 [-0.125, +0.000] | 0.500 | 1.67x | 1.45x | 8.51 [8.31, 9.02] | 9.63 [9.27, 11.21] | 0.83/1.24 | 2.92 |
| LLMLingua v1/GPT-2 (~2x) | 0.250 [0.142, 0.402] | -0.750 [-0.875, -0.600] | <0.001 | 2.36x | 1.81x | 8.07 [7.56, 9.37] | 11.67 [9.87, 12.36] | 1.56/4.11 | 6.22 |
| Selective-Context-style (2x) | 0.575 [0.422, 0.715] | -0.425 [-0.575, -0.275] | <0.001 | 1.86x | 1.56x | 7.91 [7.47, 8.20] | 9.79 [9.09, 10.66] | 0.72/1.23 | 2.75 |
| random word drop (2x) | 0.300 [0.181, 0.454] | -0.700 [-0.825, -0.550] | <0.001 | 1.83x | 1.54x | 7.15 [6.87, 7.75] | 9.25 [7.99, 10.14] | 0.00/0.00 | 0.00 |
| query-aware TF-IDF (2x) | 1.000 [0.912, 1.000] | +0.000 [+0.000, +0.000] | 1.000 | 1.90x | 1.58x | 6.89 [6.55, 7.70] | 9.23 [8.26, 10.64] | 0.00/0.01 | 0.01 |

**logs** (n=40 items, 9 arms, same prompts, llama3.2:3b on CPU)

| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s |
|---|---|---|---|---|---|---|---|---|---|
| uncompressed | 1.000 [0.912, 1.000] | - | - | 1.00x | 1.00x | 16.13 [15.48, 16.93] | 20.76 [18.07, 23.65] | 0.00/0.00 | 0.00 |
| LLMLingua-2 (~2x) | 0.300 [0.181, 0.454] | -0.700 [-0.825, -0.550] | <0.001 | 1.79x | 1.62x | 12.30 [11.84, 13.03] | 16.10 [14.17, 19.31] | 2.15/3.30 | 7.06 |
| LLMLingua-2 (~3x) | 0.225 [0.123, 0.375] | -0.775 [-0.900, -0.650] | <0.001 | 2.53x | 2.08x | 10.33 [9.47, 11.46] | 13.45 [12.39, 15.14] | 2.08/3.61 | 6.88 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.350 [0.221, 0.505] | -0.650 [-0.800, -0.500] | <0.001 | 1.71x | 1.56x | 12.53 [12.16, 13.48] | 16.43 [15.08, 17.51] | 1.72/3.03 | 6.53 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.425 [0.285, 0.578] | -0.575 [-0.725, -0.425] | <0.001 | 1.22x | 1.18x | 15.30 [14.49, 16.18] | 18.83 [17.15, 18.95] | 1.42/2.31 | 5.41 |
| LLMLingua v1/GPT-2 (~2x) | 0.200 [0.105, 0.348] | -0.800 [-0.925, -0.675] | <0.001 | 2.43x | 2.03x | 13.59 [12.81, 14.43] | 17.20 [15.14, 24.57] | 4.85/8.54 | 14.93 |
| Selective-Context-style (2x) | 0.750 [0.598, 0.858] | -0.250 [-0.400, -0.125] | 0.002 | 2.08x | 1.81x | 11.17 [10.61, 12.38] | 14.43 [13.50, 15.39] | 1.62/3.49 | 5.60 |
| random word drop (2x) | 0.175 [0.087, 0.320] | -0.825 [-0.925, -0.700] | <0.001 | 1.86x | 1.66x | 9.98 [9.55, 10.64] | 13.17 [12.11, 14.59] | 0.00/0.00 | 0.00 |
| query-aware TF-IDF (2x) | 0.950 [0.835, 0.986] | -0.050 [-0.125, +0.000] | 0.500 | 2.01x | 1.76x | 9.65 [9.07, 10.00] | 11.88 [11.07, 14.10] | 0.01/0.01 | 0.01 |

**code** (n=40 items, 9 arms, same prompts, llama3.2:3b on CPU)

| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s |
|---|---|---|---|---|---|---|---|---|---|
| uncompressed | 0.875 [0.739, 0.945] | - | - | 1.00x | 1.00x | 16.22 [14.74, 18.29] | 20.64 [19.41, 24.18] | 0.00/0.00 | 0.00 |
| LLMLingua-2 (~2x) | 0.550 [0.398, 0.693] | -0.325 [-0.475, -0.175] | 0.001 | 1.98x | 1.72x | 11.96 [11.34, 12.58] | 15.12 [13.99, 16.59] | 2.16/3.63 | 7.17 |
| LLMLingua-2 (~3x) | 0.450 [0.307, 0.602] | -0.425 [-0.575, -0.275] | <0.001 | 2.81x | 2.22x | 9.94 [9.52, 10.41] | 12.14 [10.90, 13.49] | 2.09/3.40 | 6.99 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.575 [0.422, 0.715] | -0.300 [-0.450, -0.150] | 0.002 | 1.98x | 1.72x | 10.77 [10.22, 11.94] | 14.92 [13.08, 16.31] | 1.58/1.76 | 6.27 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.750 [0.598, 0.858] | -0.125 [-0.275, +0.025] | 0.180 | 1.32x | 1.26x | 14.78 [14.14, 15.53] | 16.83 [16.11, 17.77] | 1.74/2.34 | 6.46 |
| LLMLingua v1/GPT-2 (~2x) | 0.175 [0.087, 0.320] | -0.700 [-0.825, -0.550] | <0.001 | 1.73x | 1.56x | 18.27 [16.69, 19.81] | 24.93 [20.69, 29.60] | 6.76/14.32 | 21.52 |
| Selective-Context-style (2x) | 0.725 [0.572, 0.839] | -0.150 [-0.325, +0.025] | 0.146 | 2.14x | 1.83x | 11.84 [11.25, 12.66] | 14.43 [13.51, 15.30] | 2.43/4.56 | 7.79 |
| random word drop (2x) | 0.325 [0.201, 0.480] | -0.550 [-0.725, -0.350] | <0.001 | 1.98x | 1.73x | 9.35 [8.93, 9.69] | 12.82 [11.71, 14.28] | 0.00/0.00 | 0.00 |
| query-aware TF-IDF (2x) | 0.900 [0.769, 0.960] | +0.025 [-0.075, +0.125] | 1.000 | 2.08x | 1.80x | 9.05 [8.56, 9.68] | 12.53 [10.21, 13.71] | 0.01/0.01 | 0.02 |

### B. Pooled over the three families

| arm | n | acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p |
|---|---|---|---|---|
| uncompressed | 120 | 0.958 [0.906, 0.982] | - | - |
| LLMLingua-2 (~2x) | 120 | 0.533 [0.444, 0.620] | -0.425 [-0.517, -0.333] | <0.001 |
| LLMLingua-2 (~3x) | 120 | 0.433 [0.348, 0.523] | -0.525 [-0.617, -0.433] | <0.001 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 120 | 0.550 [0.461, 0.636] | -0.408 [-0.500, -0.317] | <0.001 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 120 | 0.708 [0.622, 0.782] | -0.250 [-0.333, -0.167] | <0.001 |
| LLMLingua v1/GPT-2 (~2x) | 120 | 0.208 [0.145, 0.289] | -0.750 [-0.825, -0.675] | <0.001 |
| Selective-Context-style (2x) | 120 | 0.683 [0.596, 0.760] | -0.275 [-0.367, -0.183] | <0.001 |
| random word drop (2x) | 120 | 0.267 [0.196, 0.352] | -0.692 [-0.775, -0.600] | <0.001 |
| query-aware TF-IDF (2x) | 120 | 0.950 [0.895, 0.977] | -0.008 [-0.050, +0.033] | 1.000 |

### C. Evidence retention in the compressed context (all items, no LLM involved)

| family | arm | answer string verbatim | answer ws-insensitive | all key strings verbatim | n |
|---|---|---|---|---|---|
| qa | LLMLingua-2 (~2x) | 0.78 [0.62, 0.88] | 0.90 | 0.78 | 40 |
| qa | LLMLingua-2 (~3x) | 0.75 [0.60, 0.86] | 0.88 | 0.65 | 40 |
| qa | LLMLingua-2 + digit protection (~2x, post-hoc) | 0.82 [0.68, 0.91] | 0.95 | 0.80 | 40 |
| qa | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.88 [0.74, 0.95] | 1.00 | 0.88 | 40 |
| qa | LLMLingua v1/GPT-2 (~2x) | 0.28 [0.16, 0.43] | 0.28 | 0.28 | 40 |
| qa | Selective-Context-style (2x) | 0.93 [0.80, 0.97] | 0.93 | 0.93 | 40 |
| qa | random word drop (2x) | 0.45 [0.31, 0.60] | 0.45 | 0.40 | 40 |
| qa | query-aware TF-IDF (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 |
| logs | LLMLingua-2 (~2x) | 0.50 [0.35, 0.65] | 0.82 | 0.00 | 40 |
| logs | LLMLingua-2 (~3x) | 0.50 [0.35, 0.65] | 0.78 | 0.00 | 40 |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | 0.50 [0.35, 0.65] | 0.78 | 0.00 | 40 |
| logs | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.50 [0.35, 0.65] | 0.93 | 0.00 | 40 |
| logs | LLMLingua v1/GPT-2 (~2x) | 0.50 [0.35, 0.65] | 0.50 | 0.15 | 40 |
| logs | Selective-Context-style (2x) | 0.90 [0.77, 0.96] | 0.90 | 0.90 | 40 |
| logs | random word drop (2x) | 0.70 [0.55, 0.82] | 0.70 | 0.25 | 40 |
| logs | query-aware TF-IDF (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 |
| code | LLMLingua-2 (~2x) | 0.70 [0.55, 0.82] | 1.00 | 0.00 | 40 |
| code | LLMLingua-2 (~3x) | 0.70 [0.55, 0.82] | 0.97 | 0.00 | 40 |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | 0.70 [0.55, 0.82] | 1.00 | 0.00 | 40 |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.70 [0.55, 0.82] | 1.00 | 0.00 | 40 |
| code | LLMLingua v1/GPT-2 (~2x) | 0.40 [0.26, 0.55] | 0.40 | 0.05 | 40 |
| code | Selective-Context-style (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 |
| code | random word drop (2x) | 0.62 [0.47, 0.76] | 0.62 | 0.60 | 40 |
| code | query-aware TF-IDF (2x) | 1.00 [0.91, 1.00] | 1.00 | 1.00 | 40 |

### D. PII / sensitive-field survival (50 synthetic records; verbatim string present after compression)

| arm | ctx ratio | name | dob | address | email | phone | national_id | iban | diagnosis | case_ref | ALL_FIELDS_INTACT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LLMLingua-2 (~2x) | 2.37x | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 (ws 1.00) | 0.94 | 1.00 | 0.66 | 0.00 (ws 0.78) | 0.00 |
| LLMLingua-2 (~3x) | 3.47x | 0.98 | 0.00 | 0.00 | 0.00 | 0.00 (ws 0.52) | 0.86 | 0.76 | 0.66 | 0.00 | 0.00 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 2.32x | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 (ws 1.00) | 1.00 | 1.00 | 0.66 | 0.00 (ws 0.52) | 0.00 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 1.61x | 1.00 | 0.00 (ws 1.00) | 0.00 | 0.00 (ws 0.04) | 0.00 (ws 1.00) | 1.00 | 1.00 | 0.66 | 0.00 (ws 1.00) | 0.00 |
| LLMLingua v1/GPT-2 (~2x) | 1.73x | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.84 | 0.00 | 0.00 |
| Selective-Context-style (2x) | 1.63x | 1.00 | 1.00 | 0.40 | 1.00 | 1.00 | 0.96 | 1.00 | 0.52 | 1.00 | 0.18 |
| random word drop (2x) | 1.82x | 0.30 | 0.58 | 0.12 | 0.52 | 0.20 | 0.14 | 0.42 | 0.40 | 0.52 | 0.00 |

### E. Failure attribution (wrong answers: evidence lost in compression vs evidence present but still wrong)

| family | arm | wrong | evidence lost | evidence present | wrong where base was right |
|---|---|---|---|---|---|
| qa | LLMLingua-2 (~2x) | 10 | 4 | 6 | 10 |
| qa | LLMLingua-2 (~3x) | 15 | 5 | 10 | 15 |
| qa | LLMLingua-2 + digit protection (~2x, post-hoc) | 11 | 2 | 9 | 11 |
| qa | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 2 | 0 | 2 | 2 |
| qa | LLMLingua v1/GPT-2 (~2x) | 30 | 29 | 1 | 30 |
| qa | Selective-Context-style (2x) | 17 | 3 | 14 | 17 |
| qa | random word drop (2x) | 28 | 22 | 6 | 28 |
| qa | query-aware TF-IDF (2x) | 0 | 0 | 0 | 0 |
| logs | LLMLingua-2 (~2x) | 28 | 7 | 21 | 28 |
| logs | LLMLingua-2 (~3x) | 31 | 9 | 22 | 31 |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | 26 | 9 | 17 | 26 |
| logs | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 23 | 3 | 20 | 23 |
| logs | LLMLingua v1/GPT-2 (~2x) | 32 | 20 | 12 | 32 |
| logs | Selective-Context-style (2x) | 10 | 4 | 6 | 10 |
| logs | random word drop (2x) | 33 | 12 | 21 | 33 |
| logs | query-aware TF-IDF (2x) | 2 | 0 | 2 | 2 |
| code | LLMLingua-2 (~2x) | 18 | 0 | 18 | 14 |
| code | LLMLingua-2 (~3x) | 22 | 1 | 21 | 17 |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | 17 | 0 | 17 | 13 |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 10 | 0 | 10 | 7 |
| code | LLMLingua v1/GPT-2 (~2x) | 33 | 24 | 9 | 28 |
| code | Selective-Context-style (2x) | 11 | 0 | 11 | 9 |
| code | random word drop (2x) | 27 | 15 | 12 | 24 |
| code | query-aware TF-IDF (2x) | 4 | 0 | 4 | 2 |

### F. Pairs of compressors that the sample cannot separate (exact McNemar p >= 0.05)

| family | A | B | A-only right | B-only right | acc diff A-B | p |
|---|---|---|---|---|---|---|
| qa | LLMLingua-2 (~2x) | LLMLingua-2 (~3x) | 6 | 1 | +0.125 | 0.125 |
| qa | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 2 | 1 | +0.025 | 1.000 |
| qa | LLMLingua-2 (~2x) | Selective-Context-style (2x) | 11 | 4 | +0.175 | 0.118 |
| qa | LLMLingua-2 (~3x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 1 | 5 | -0.100 | 0.219 |
| qa | LLMLingua-2 (~3x) | Selective-Context-style (2x) | 10 | 8 | +0.050 | 0.815 |
| qa | LLMLingua-2 + digit protection (~2x, post-hoc) | Selective-Context-style (2x) | 10 | 4 | +0.150 | 0.180 |
| qa | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | query-aware TF-IDF (2x) | 0 | 2 | -0.050 | 0.500 |
| qa | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 7 | 9 | -0.050 | 0.804 |
| logs | LLMLingua-2 (~2x) | LLMLingua-2 (~3x) | 5 | 2 | +0.075 | 0.453 |
| logs | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 2 | 4 | -0.050 | 0.688 |
| logs | LLMLingua-2 (~2x) | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0 | 5 | -0.125 | 0.062 |
| logs | LLMLingua-2 (~2x) | LLMLingua v1/GPT-2 (~2x) | 8 | 4 | +0.100 | 0.388 |
| logs | LLMLingua-2 (~2x) | random word drop (2x) | 10 | 5 | +0.125 | 0.302 |
| logs | LLMLingua-2 (~3x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 1 | 6 | -0.125 | 0.125 |
| logs | LLMLingua-2 (~3x) | LLMLingua v1/GPT-2 (~2x) | 6 | 5 | +0.025 | 1.000 |
| logs | LLMLingua-2 (~3x) | random word drop (2x) | 7 | 5 | +0.050 | 0.774 |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 1 | 4 | -0.075 | 0.375 |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | LLMLingua v1/GPT-2 (~2x) | 11 | 5 | +0.150 | 0.210 |
| logs | LLMLingua-2 + digit protection (~2x, post-hoc) | random word drop (2x) | 11 | 4 | +0.175 | 0.118 |
| logs | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 8 | 7 | +0.025 | 1.000 |
| code | LLMLingua-2 (~2x) | LLMLingua-2 (~3x) | 5 | 1 | +0.100 | 0.219 |
| code | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 0 | 1 | -0.025 | 1.000 |
| code | LLMLingua-2 (~2x) | random word drop (2x) | 17 | 8 | +0.225 | 0.108 |
| code | LLMLingua-2 (~3x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 0 | 5 | -0.125 | 0.062 |
| code | LLMLingua-2 (~3x) | random word drop (2x) | 15 | 10 | +0.125 | 0.424 |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | Selective-Context-style (2x) | 1 | 7 | -0.150 | 0.070 |
| code | LLMLingua-2 + digit protection (~2x, post-hoc) | random word drop (2x) | 18 | 8 | +0.250 | 0.076 |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | Selective-Context-style (2x) | 4 | 3 | +0.025 | 1.000 |
| code | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | query-aware TF-IDF (2x) | 2 | 8 | -0.150 | 0.109 |
| code | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 6 | 12 | -0.150 | 0.238 |
| code | Selective-Context-style (2x) | query-aware TF-IDF (2x) | 3 | 10 | -0.175 | 0.092 |
| pooled | LLMLingua-2 (~2x) | LLMLingua-2 + digit protection (~2x, post-hoc) | 4 | 6 | -0.017 | 0.754 |
| pooled | LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | Selective-Context-style (2x) | 23 | 20 | +0.025 | 0.761 |
| pooled | LLMLingua v1/GPT-2 (~2x) | random word drop (2x) | 21 | 28 | -0.058 | 0.392 |

### G. Latency model fitted on this machine (CPU target)

Uncached prefill (baseline prompts): median 23.6 ms/token (p10-p90 19.9-31.9); decode median 73.2 ms/token.

Compression saves wall time only if the target's own prefill is slower than the break-even column (ms per prompt token); on this CPU the target prefills at the median above. Compressor cost is total wall time divided by total input tokens over all 120 test items.

| arm | compressor wall, ms per input token | compressor CPU-s per 1k input tokens | mean ratio | break-even target prefill, ms/token |
|---|---|---|---|---|
| LLMLingua-2 (~2x) | 4.67 | 14.22 | 2.05x | 9.1 |
| LLMLingua-2 (~3x) | 4.70 | 13.94 | 2.83x | 7.3 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 3.63 | 12.88 | 2.01x | 7.2 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 3.50 | 11.96 | 1.40x | 12.2 |
| LLMLingua v1/GPT-2 (~2x) | 13.25 | 34.48 | 2.18x | 24.4 |
| Selective-Context-style (2x) | 4.62 | 13.04 | 2.03x | 9.1 |
| random word drop (2x) | 0.00 | 0.00 | 1.89x | none (compressor cost about 0) |
| query-aware TF-IDF (2x) | 0.01 | 0.04 | 2.01x | none (compressor cost about 0) |

### H. Structure survival (no LLM involved): share of the original's structural strings that appear verbatim in the compressed text

| arm | `logs:svc=` | `logs:req=` | `logs:status=` | `logs:latency_ms=` | `logs:user=` | `logs:region=` | `code:def ` | `code:return` | `code:MAX_` | spurious ` _ ` per code file |
|---|---|---|---|---|---|---|---|---|---|---|
| LLMLingua-2 (~2x) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.43 | 0.00 | 27.1 |
| LLMLingua-2 (~3x) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.09 | 0.00 | 18.8 |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.43 | 0.00 | 27.1 |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.49 | 0.91 | 0.00 | 45.6 |
| LLMLingua v1/GPT-2 (~2x) | 0.08 | 0.10 | 0.07 | 0.16 | 0.17 | 0.12 | 0.13 | 0.36 | 0.06 | 0.0 |
| Selective-Context-style (2x) | 0.53 | 1.00 | 0.10 | 0.53 | 1.00 | 0.24 | 0.03 | 0.78 | 0.52 | 0.0 |
| random word drop (2x) | 0.56 | 0.49 | 0.55 | 0.59 | 0.57 | 0.56 | 0.58 | 0.53 | 0.56 | 0.0 |
| query-aware TF-IDF (2x) | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.46 | 0.46 | 0.55 | 0.0 |

### I. Structured family split by record type (20 plain-text log items, 20 JSON items; accuracy with Wilson 95% interval)

| arm | log lines (n=20) | JSON records (n=20) |
|---|---|---|
| uncompressed | 1.00 [0.84, 1.00] | 1.00 [0.84, 1.00] |
| LLMLingua-2 (~2x) | 0.20 [0.08, 0.42] | 0.40 [0.22, 0.61] |
| LLMLingua-2 (~3x) | 0.10 [0.03, 0.30] | 0.35 [0.18, 0.57] |
| LLMLingua-2 + digit protection (~2x, post-hoc) | 0.25 [0.11, 0.47] | 0.45 [0.26, 0.66] |
| LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc) | 0.30 [0.15, 0.52] | 0.55 [0.34, 0.74] |
| LLMLingua v1/GPT-2 (~2x) | 0.20 [0.08, 0.42] | 0.20 [0.08, 0.42] |
| Selective-Context-style (2x) | 0.55 [0.34, 0.74] | 0.95 [0.76, 0.99] |
| random word drop (2x) | 0.15 [0.05, 0.36] | 0.20 [0.08, 0.42] |
| query-aware TF-IDF (2x) | 0.95 [0.76, 0.99] | 0.95 [0.76, 0.99] |

### J. Repeat of the uncompressed baseline in the later (post-hoc) session: same prompts, new nonce, temperature 0

| family | items | identical responses | same right/wrong verdict | LLM wall p50, main run s | LLM wall p50, repeat s | repeat / main |
|---|---|---|---|---|---|---|
| qa | 40 | 40 | 40 | 10.59 | 10.77 | 1.02x |
| logs | 40 | 39 | 39 | 16.13 | 15.99 | 0.99x |
| code | 40 | 38 | 39 | 16.22 | 15.54 | 0.96x |
