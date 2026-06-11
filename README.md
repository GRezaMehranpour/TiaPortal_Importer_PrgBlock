# TIA Portal Project Importer

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![TIA Portal](https://img.shields.io/badge/TIA%20Portal-V17%20(Tested)-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An automated tool to bulk-import PLC blocks (XML) into Siemens TIA Portal projects. This tool preserves folder structures by automatically creating Groups/Folders within the TIA "Program blocks" section based on your local directory structure.

## 🚀 Features

- **Automated Directory Mapping:** Mirrors your local Windows folder structure into TIA Portal Block Groups.
- **Multi-Threaded GUI:** The interface remains responsive during the long-running TIA Openness import process.
- **Real-time Logging:** Detailed status updates and log file generation for troubleshooting.
- **Safety First:** Validates paths before starting the TIA Portal instance.

## 📋 Prerequisites

Before using this tool, ensure you have:

1. **Siemens TIA Portal** (V17 recommended) installed.
2. **TIA Portal Openness** installed and the current user added to the `Siemens TIA Openness` local user group.
3. **Python 3.8+** installed.
4. The **`siemens_tia_scripting`** library (or your specific Openness wrapper) configured in your Python environment.

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/TIA-Portal-Importer.git
   cd TIA-Portal-Importer