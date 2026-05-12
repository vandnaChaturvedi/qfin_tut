# Qiskit Finance Tutorial Environment Setup

This guide sets up the `qfin` enviornment and steps for running all 12 qiskit-finance tutorials.

---

## Prerequisites

- Anaconda or Miniconda
- Python 3.12

---

## Setup Steps
```bash
conda create --name qfin python=3.12
conda activate qfin
git clone https://github.com/vandnaChaturvedi/qiskit_finance_tutorial.git
cd qiskit_finance_tutorial
pip install -r requirements.txt 
jupyter lab
```
---

## Package Versions (tested and working)

| Package             | Version |
|---------------------|---------|
| qiskit              | 2.4.1   |
| qiskit-aer          | 0.17.2  |
| qiskit-algorithms   | 0.4.0   |
| qiskit-finance      | 0.4.1   |
| qiskit-optimization | 0.7.0   |
| Python              | 3.12    |

---

