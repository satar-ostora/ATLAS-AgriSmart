# 🌿 ATLAS AgriSmart — IoT Smart Agriculture Dashboard

> **"ATLAS voit, ATLAS agit"**  
> A real-time IoT dashboard for precision agriculture, built with Python and CustomTkinter.

---

## 📌 Overview

ATLAS AgriSmart is a desktop monitoring application that collects, visualizes, and analyzes sensor data from IoT devices deployed across agricultural zones. It connects directly to Arduino-based sensors via serial port and displays live metrics for soil, air, and water conditions — with intelligent alerts and agronomic recommendations.

This project was developed as part of a smart farming initiative to help farmers make data-driven decisions and prevent crop loss.

---

## 🗂️ Project Structure

```
ATLAS-AgriSmart/
│
├── dashbord_smart_farme.py     # Main GUI dashboard application (CustomTkinter)
├── PythonApplication7.py       # Serial collector: Arduino → CSV pipeline
├── agri_data.csv               # Sample sensor dataset (multi-zone, timestamped)
└── README.md                   # Project documentation (this file)
```

---

## ✨ Features

### 🖥️ Dashboard (`dashbord_smart_farme.py`)
- **Interactive Zone Map** — Visual grid showing health status of each agricultural zone (green / amber / red)
- **Real-time Sensor Cards** — Displays the latest values for 12 sensor metrics grouped by category (Soil · Air · Water)
- **Zone Health Score** — Composite score (0–100) per zone based on threshold compliance
- **Charts & Trends** — Time-series line chart, bar chart of recent readings, and cross-zone comparison
- **Alerts & Recommendations** — Prioritized alert list with actionable agronomic advice per zone
- **Auto-load CSV** — Automatically loads `agri_data.csv` on startup if present

### 📡 Serial Collector (`PythonApplication7.py`)
- Auto-detects the Arduino USB port (Windows / Linux / macOS)
- Supports two Arduino output formats: native CSV and human-readable text
- Writes data incrementally to `agri_data.csv` in real time
- Compatible with the `AgroDrone_CSV.ino` Arduino sketch

---

## 🌡️ Monitored Sensors

| Category | Sensor | Unit | Optimal Range |
|----------|--------|------|---------------|
| 🪱 **Soil** | Moisture (`sol_hum`) | % | 35 – 70 |
| 🪱 **Soil** | Temperature (`sol_temp`) | °C | 15 – 28 |
| 🪱 **Soil** | pH (`sol_ph`) | — | 5.5 – 7.2 |
| 🪱 **Soil** | Electrical Conductivity (`sol_ec`) | dS/m | 0.6 – 2.0 |
| 🌬️ **Air** | Temperature (`air_temp`) | °C | 15 – 30 |
| 🌬️ **Air** | Humidity (`air_hum`) | % | 40 – 70 |
| 🌬️ **Air** | CO₂ (`air_co2`) | ppm | 350 – 450 |
| 🌬️ **Air** | Wind Speed (`air_vent`) | km/h | 2 – 15 |
| 💧 **Water** | pH (`eau_ph`) | — | 6.5 – 7.5 |
| 💧 **Water** | Turbidity (`eau_turb`) | NTU | 0 – 5 |
| 💧 **Water** | Reservoir Level (`eau_niveau`) | % | 40 – 100 |
| 💧 **Water** | Flow Rate (`eau_debit`) | L/min | 1 – 5 |

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10+**
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/atlas-agrismart.git
cd atlas-agrismart

# 2. Install dependencies
pip install customtkinter pandas matplotlib pyserial
```

### Running the Dashboard

```bash
python dashbord_smart_farme.py
```

> The dashboard will automatically load `agri_data.csv` if it is in the same folder.  
> You can also load any CSV file manually via the **"Charger CSV"** button in the sidebar.

### Running the Serial Collector

Connect your Arduino, then run:

```bash
# Auto-detect port
python PythonApplication7.py

# Specify port manually
python PythonApplication7.py --port COM3            # Windows
python PythonApplication7.py --port /dev/ttyUSB0    # Linux
python PythonApplication7.py --port /dev/cu.usbmodem14101  # macOS

# Additional options
python PythonApplication7.py --baud 9600 --zone A --append --verbose
```

---

## 📄 CSV Data Format

The `agri_data.csv` file must follow this structure:

```csv
timestamp,zone,sol_hum,sol_temp,sol_ph,sol_ec,air_temp,air_hum,air_co2,air_vent,eau_ph,eau_turb,eau_niveau,eau_debit
2024-01-18 00:00,A,44,21.5,6.8,1.2,24.3,55,410,8,7.1,2.1,78,3.2
2024-01-18 01:00,B,38,20.8,6.5,0.9,23.1,60,395,6,7.0,1.8,65,2.8
```

| Field | Description |
|-------|-------------|
| `timestamp` | ISO datetime: `YYYY-MM-DD HH:MM:SS` |
| `zone` | Zone identifier (e.g., `A`, `B`, `1`, `2`) |
| Other fields | Numeric sensor values as described in the table above |

---

## 🛠️ Dependencies

| Package | Purpose |
|---------|---------|
| `customtkinter` | Modern Tkinter UI framework |
| `pandas` | CSV data loading and manipulation |
| `matplotlib` | Charts and data visualization |
| `pyserial` | Serial communication with Arduino |

---

## 📸 Screenshots

<img width="1914" height="1016" alt="image" src="https://github.com/user-attachments/assets/934463a4-3966-486a-aa06-35700da289ba" />


## 🔧 Arduino Integration

This dashboard is designed to work with an **Arduino** microcontroller running the `AgroDrone_CSV.ino` sketch. The Arduino reads from:
- Soil moisture, temperature, pH, and EC sensors
- DHT22 / DHT11 (air temperature & humidity)
- MQ-135 (CO₂ / air quality)
- Ultrasonic or float sensor (water level)

Data is transmitted over USB serial at 9600 baud in CSV format and captured by `PythonApplication7.py`.

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License. See `LICENSE` for details.

---

## 👥 Authors

- **ATLAS Team** — *Smart Agriculture IoT Prototype*

---

*Built with ❤️ for precision agriculture.*
